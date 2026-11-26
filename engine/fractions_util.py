from fractions import Fraction
from typing import Union

def parse_fraction(val: Union[str, float, int, Fraction]) -> Fraction:
    """
    Converts an input (a string such as '1/3', float, int, Fraction) into a Fraction object.
    """
    if isinstance(val, Fraction):
        return val
    if isinstance(val, int):
        return Fraction(val, 1)
    if isinstance(val, float):
        # Use limit_denominator to recover the common Saaty fractions (1/9 to 9)
        return Fraction(val).limit_denominator(18)
    if isinstance(val, str):
        val_str = val.strip()
        if "/" in val_str:
            parts = val_str.split("/")
            if len(parts) == 2:
                num = int(parts[0].strip())
                den = int(parts[1].strip())
                if den == 0:
                    raise ZeroDivisionError("The denominator of a fraction cannot be zero.")
                return Fraction(num, den)
            raise ValueError(f"Invalid fraction format: {val}")
        # Coba konversi float/int string
        f_val = float(val_str)
        if f_val.is_integer():
            return Fraction(int(f_val), 1)
        return Fraction(f_val).limit_denominator(18)
    raise TypeError(f"Unsupported type for a fraction: {type(val)}")

def fraction_to_float(val: Union[str, float, int, Fraction]) -> float:
    """Converts a fraction input to a Python float."""
    frac = parse_fraction(val)
    return float(frac)

def format_fraction(val: Union[str, float, int, Fraction]) -> str:
    """
    Returns a user-friendly text representation:
    1 -> '1'
    Fraction(1, 3) -> '1/3'
    3 -> '3'
    """
    frac = parse_fraction(val)
    if frac.denominator == 1:
        return str(frac.numerator)
    return f"{frac.numerator}/{frac.denominator}"

def format_saaty_display(val: Union[str, float, int, Fraction], decimals: int = 3) -> str:
    """
    Display format of a Saaty value, for example:
    '1' for 1
    '1/3 (0.333)' for 1/3
    '3 (3.000)' or just '3' for a whole number
    """
    frac = parse_fraction(val)
    flt = float(frac)
    if frac.denominator == 1:
        return str(frac.numerator)
    return f"{frac.numerator}/{frac.denominator} ({flt:.{decimals}f})"
