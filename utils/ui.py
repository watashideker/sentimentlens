"""Shared UI pieces: module icons and the centered title card shown at the top of each module."""

import streamlit as st

# Material Symbols Rounded names, shared by the nav, Home cards and title cards
ICONS = {"sentiment": "find_in_page", "stock": "candlestick_chart"}


def icon_badge(module: str) -> str:
    """Rounded-square badge holding the module icon, tinted by the module accent."""
    return f'<span class="fl-badge"><span class="material-symbols-rounded">{ICONS[module]}</span></span>'


def title_card(module: str, name: str, description: str) -> None:
    """Render the module's title card: logo mark, name and a one-line description."""
    st.markdown(
        f'<div class="finlens-titlecard">{icon_badge(module)}<h1>{name}</h1><p>{description}</p></div>',
        unsafe_allow_html=True,
    )
