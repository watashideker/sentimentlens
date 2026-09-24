import io

import pytest
from docx import Document
from pypdf import PdfWriter

from ingest import CHUNK_OVERLAP, CHUNK_SIZE, Chunk, ingest_file, split_text


def make_pdf(page_texts):
    """Build a minimal PDF with one text line per page (blank string = empty page)."""
    objs = []  # index i -> object number i+1
    n = len(page_texts)
    objs.append("<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{4 + 2 * i} 0 R" for i in range(n))
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>")
    objs.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for i, text in enumerate(page_texts):
        content_id = 5 + 2 * i
        objs.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        )
        stream = f"BT /F1 12 Tf 50 700 Td ({text}) Tj ET" if text else ""
        objs.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return bytes(out)


def make_docx(paragraphs):
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


LONG_TEXT = " ".join(
    f"Sentence number {i} talks about product feedback and sentiment." for i in range(60)
)


def test_txt_returns_chunks():
    chunks = ingest_file(b"Hello world. This is a test.", "note.txt")
    assert len(chunks) == 1
    c = chunks[0]
    assert isinstance(c, Chunk)
    assert c.text == "Hello world. This is a test."
    assert c.source == "note.txt"
    assert c.page is None


def test_chunk_sizes_and_overlap():
    chunks = split_text(LONG_TEXT)
    assert len(chunks) > 2
    assert all(len(c) <= CHUNK_SIZE for c in chunks)
    for prev, nxt in zip(chunks, chunks[1:]):
        # the start of the next chunk repeats the tail of the previous one
        assert nxt[:30] in prev
        assert len(prev) - prev.rfind(nxt[:30]) <= CHUNK_OVERLAP + 30


def test_breaks_at_sentence_boundaries():
    chunks = split_text(LONG_TEXT)
    for c in chunks[:-1]:
        assert c.endswith(".")


def test_prefers_paragraph_boundaries():
    para = "A" * 50 + ". " + "B" * 400 + "."
    text = para + "\n\n" + para + "\n\n" + para
    chunks = split_text(text)
    assert chunks[0] == para


def test_no_infinite_loop_on_unbroken_text():
    chunks = split_text("x" * 5000)
    assert all(len(c) <= CHUNK_SIZE for c in chunks)
    assert sum(len(c) for c in chunks) >= 5000


def test_chunk_ids_unique():
    chunks = ingest_file(LONG_TEXT.encode(), "a.txt")
    assert len({c.id for c in chunks}) == len(chunks)


def test_pdf_keeps_page_numbers():
    data = make_pdf(["First page text.", "", "Third page text."])
    chunks = ingest_file(data, "doc.pdf")
    assert [c.page for c in chunks] == [1, 3]
    assert "First page" in chunks[0].text
    assert "Third page" in chunks[1].text
    assert all(c.source == "doc.pdf" for c in chunks)
    assert len({c.id for c in chunks}) == 2


def test_pdf_without_text_raises():
    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.write(buf)
    with pytest.raises(ValueError, match="no extractable text"):
        ingest_file(buf.getvalue(), "scan.pdf")


def test_corrupt_pdf_raises_valueerror():
    with pytest.raises(ValueError, match="Could not read PDF"):
        ingest_file(b"not a pdf", "bad.pdf")


def test_docx_extraction():
    data = make_docx(["First paragraph.", "Second paragraph."])
    chunks = ingest_file(data, "r.docx")
    assert "First paragraph." in chunks[0].text
    assert "Second paragraph." in chunks[0].text
    assert chunks[0].page is None


def test_empty_docx_raises():
    with pytest.raises(ValueError, match="no text"):
        ingest_file(make_docx([]), "empty.docx")


def test_empty_file_raises():
    with pytest.raises(ValueError, match="empty"):
        ingest_file(b"", "x.txt")


def test_whitespace_only_txt_raises():
    with pytest.raises(ValueError, match="no text"):
        ingest_file(b"  \n\n \t ", "x.txt")


def test_unsupported_extension_raises():
    with pytest.raises(ValueError, match="Unsupported"):
        ingest_file(b"data", "image.png")


def test_latin1_txt_fallback():
    chunks = ingest_file("café".encode("latin-1"), "l.txt")
    assert chunks[0].text == "café"
