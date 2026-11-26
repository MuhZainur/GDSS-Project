import json
from pathlib import Path
from fractions import Fraction
import pytest

from engine.fractions_util import (
    parse_fraction,
    fraction_to_float,
    format_fraction,
    format_saaty_display
)
from engine.schemas import Session

def test_parse_fraction_strings():
    assert parse_fraction("1/3") == Fraction(1, 3)
    assert parse_fraction("3/1") == Fraction(3, 1)
    assert parse_fraction("2") == Fraction(2, 1)
    assert parse_fraction("0.5") == Fraction(1, 2)
    assert parse_fraction(" 1 / 4 ") == Fraction(1, 4)

def test_fraction_to_float():
    assert abs(fraction_to_float("1/2") - 0.5) < 1e-9
    assert abs(fraction_to_float("1/3") - 1/3) < 1e-9
    assert abs(fraction_to_float(2) - 2.0) < 1e-9

def test_format_fraction():
    assert format_fraction(1) == "1"
    assert format_fraction("1/3") == "1/3"
    assert format_fraction(Fraction(2, 1)) == "2"
    assert format_fraction(0.25) == "1/4"

def test_format_saaty_display():
    assert format_saaty_display(1) == "1"
    assert "1/3 (0.333)" in format_saaty_display("1/3")
    assert format_saaty_display(3) == "3"

def test_load_sample_case():
    data_path = Path(__file__).resolve().parent.parent / "data" / "sample_case.json"
    assert data_path.exists(), f"File {data_path} not found"
    with open(data_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    session = Session.model_validate(raw_data)
    assert session.session_id == "nusacompute-2026"
    assert len(session.alternatives) == 7
    assert len(session.criteria) == 7
    assert len(session.dms) == 5
    assert "DM1" in session.dm_inputs
    assert len(session.dm_inputs["DM1"].pairwise) == 4
