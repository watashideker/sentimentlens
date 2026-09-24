"""Shared UI pieces: the centered title card shown at the top of each module."""

import streamlit as st

# Marks draw in currentColor, which the stylesheet sets to the module accent.
MARKS = {
    "sentiment": (
        '<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true"><circle cx="26" cy="26" r="18"/>'
        '<polyline points="13,32 20,25 26,29 38,17"/><line x1="39" y1="39" x2="56" y2="56" stroke-width="6"/></svg>'
    ),
    "stock": (
        '<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true"><line x1="16" y1="8" x2="16" y2="56"/>'
        '<rect x="10" y="20" width="12" height="20" rx="2"/><line x1="32" y1="14" x2="32" y2="50"/>'
        '<rect x="26" y="26" width="12" height="16" rx="2"/><line x1="48" y1="6" x2="48" y2="46"/>'
        '<rect x="42" y="14" width="12" height="22" rx="2"/></svg>'
    ),
}


def title_card(module: str, name: str, description: str) -> None:
    """Render the module's title card: logo mark, name and a one-line description."""
    st.markdown(
        f'<div class="finlens-titlecard">{MARKS[module]}<h1>{name}</h1><p>{description}</p></div>',
        unsafe_allow_html=True,
    )
