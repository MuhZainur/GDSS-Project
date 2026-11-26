from typing import Union

import streamlit as st

from app.labels import SAATY_WORDS
from app.theme import esc, render_html

# Slider positions: -8..-1 = A more important (scale 9..2), 0 = equal, 1..8 = B more important (scale 2..9).
SLIDER_OPTIONS = list(range(-8, 9))


def _to_slider_val(val: Union[str, float, int]) -> int:
    """Maps a stored AHP value (2..9, 1, or '1/2'..'1/9') to a slider position."""
    try:
        if isinstance(val, str):
            s = val.strip()
            if "/" in s:
                num, den = s.split("/", 1)
                v = float(num) / float(den)
            else:
                v = float(s)
        else:
            v = float(val)
    except (ValueError, ZeroDivisionError):
        return 0
    if v > 1.0001:
        return -(min(9, round(v)) - 1)
    if 0 < v < 0.9999:
        return min(9, round(1.0 / v)) - 1
    return 0


def _tick(pos: int) -> str:
    if pos < 0:
        return f"◀ {-pos + 1}"
    if pos > 0:
        return f"{pos + 1} ▶"
    return "equal"


def render_pairwise_slider(
    label_a: str,
    label_b: str,
    key: str,
    current_val: Union[str, float, int] = 1,
) -> Union[str, int]:
    """
    One comparison row: [Criterion A] -slider- [Criterion B].
    Returns the value of A relative to B on the Saaty scale:
      A more important -> int 2..9 | equal -> 1 | B more important -> '1/2'..'1/9'
    """
    col_a, col_s, col_b = st.columns([2.2, 4.6, 2.2], vertical_alignment="center")
    with col_a:
        render_html(f'<div style="text-align:right;font-weight:500;line-height:1.25">{esc(label_a)}</div>')
    with col_s:
        pos = st.select_slider(
            f"{label_a} vs {label_b}",
            options=SLIDER_OPTIONS,
            value=_to_slider_val(current_val),
            format_func=_tick,
            key=key,
            label_visibility="collapsed",
        )
    with col_b:
        render_html(f'<div style="font-weight:500;line-height:1.25">{esc(label_b)}</div>')

    if pos < 0:
        k = -pos + 1
        word = SAATY_WORDS.get(k, "")
        render_html(f'<div class="step-note" style="margin:-0.35rem 0 0.7rem;text-align:center">{esc(label_a)} is {esc(word)} more important ({k}×)</div>')
        return k
    if pos > 0:
        k = pos + 1
        word = SAATY_WORDS.get(k, "")
        render_html(f'<div class="step-note" style="margin:-0.35rem 0 0.7rem;text-align:center">{esc(label_b)} is {esc(word)} more important ({k}×)</div>')
        return f"1/{k}"
    render_html('<div class="step-note" style="margin:-0.35rem 0 0.7rem;text-align:center">Equally important (1×)</div>')
    return 1
