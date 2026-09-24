"""Extract text from uploaded PDF/DOCX/TXT files and split it into overlapping chunks."""

import io
import re
from pathlib import PurePath

from docx import Document
from pydantic import BaseModel
from pypdf import PdfReader

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt")

_SENTENCE_END = re.compile(r"[.!?][\"')\]]*\s")


class Chunk(BaseModel):
    id: str
    text: str
    page: int | None = None  # 1-based page number; None for formats without pages
    source: str


def _extract_pdf(data: bytes) -> list[tuple[int | None, str]]:
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [(i, page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]
    except Exception as exc:
        raise ValueError(f"Could not read PDF: {exc}") from exc
    pages = [(n, t) for n, t in pages if t.strip()]
    if not pages:
        raise ValueError(
            "The PDF contains no extractable text (it may be a scanned image)."
        )
    return pages


def _extract_docx(data: bytes) -> list[tuple[int | None, str]]:
    try:
        doc = Document(io.BytesIO(data))
    except Exception as exc:
        raise ValueError(f"Could not read DOCX: {exc}") from exc
    text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [(None, text)]


def _extract_txt(data: bytes) -> list[tuple[int | None, str]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    return [(None, text)]


def _find_break(text: str, start: int, end: int) -> int:
    """Pick the best cut point in (start, end], preferring paragraph, then sentence, then word."""
    lo = start + CHUNK_SIZE // 2  # avoid tiny chunks
    window = text[lo:end]

    idx = window.rfind("\n\n")
    if idx != -1:
        return lo + idx + 2
    ends = [m.end() for m in _SENTENCE_END.finditer(window)]
    if ends:
        return lo + ends[-1]
    idx = window.rfind("\n")
    if idx != -1:
        return lo + idx + 1
    idx = window.rfind(" ")
    if idx != -1:
        return lo + idx + 1
    return end


def split_text(
    text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP
) -> list[str]:
    """Split text into ~chunk_size pieces with `overlap` characters shared between neighbours."""
    text = re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            end = _find_break(text, start, end)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        nxt = max(end - overlap, start + 1)
        # Start the overlap on a word boundary rather than mid-word.
        if nxt > 0 and not text[nxt - 1].isspace():
            space = text.find(" ", nxt, end)
            nxt = space + 1 if space != -1 else end
        start = nxt
    return chunks


def ingest_file(data: bytes, filename: str) -> list[Chunk]:
    """Extract text from an uploaded PDF, DOCX or TXT file and return it as chunks."""
    if not data:
        raise ValueError(f"'{filename}' is empty.")
    ext = PurePath(filename).suffix.lower()
    if ext == ".pdf":
        sections = _extract_pdf(data)
    elif ext == ".docx":
        sections = _extract_docx(data)
    elif ext == ".txt":
        sections = _extract_txt(data)
    else:
        raise ValueError(
            f"Unsupported file type '{ext or filename}'. Supported: PDF, DOCX, TXT."
        )

    chunks: list[Chunk] = []
    for page, text in sections:
        for i, piece in enumerate(split_text(text)):
            chunk_id = f"{filename}:p{page}:c{i}" if page else f"{filename}:c{len(chunks)}"
            chunks.append(Chunk(id=chunk_id, text=piece, page=page, source=filename))
    if not chunks:
        raise ValueError(f"'{filename}' contains no text.")
    return chunks
