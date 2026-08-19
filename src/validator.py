"""
validator.py
------------
Validates a raw uploaded DataFrame (from CSV/Excel) against the schema
defined in data/schema.py, BEFORE any transformation happens.

Design goal: fail loudly and specifically. A user dropping in a file from
a new industry should get a precise, actionable error report, not a
stack trace.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from data.schema import REQUIRED_COLUMN_NAMES, REQUIRED_COLUMNS, ColumnSpec


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0

    def summary(self) -> str:
        lines = []
        if self.is_valid:
            lines.append(f"✅ Validation passed — {self.row_count} rows.")
        else:
            lines.append(f"❌ Validation failed — {len(self.errors)} error(s).")
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARNING: {w}")
        return "\n".join(lines)


def _check_columns_present(df: pd.DataFrame, result: ValidationResult) -> None:
    missing = [c for c in REQUIRED_COLUMN_NAMES if c not in df.columns]
    if missing:
        result.errors.append(
            f"Missing required column(s): {missing}. "
            f"Expected schema: {REQUIRED_COLUMN_NAMES}"
        )

    extra = [c for c in df.columns if c not in REQUIRED_COLUMN_NAMES]
    if extra:
        result.warnings.append(
            f"Unrecognized column(s) will be ignored: {extra}"
        )


def _check_dtype(df: pd.DataFrame, spec: ColumnSpec, result: ValidationResult) -> None:
    series = df[spec.name]

    if spec.dtype == "date":
        parsed = pd.to_datetime(series, errors="coerce")
        bad = parsed.isna() & series.notna()
        if bad.any():
            result.errors.append(
                f"Column '{spec.name}': {bad.sum()} value(s) could not be parsed as dates "
                f"(e.g. row {series[bad].index[0]}: '{series[bad].iloc[0]}')."
            )

    elif spec.dtype in ("float", "int"):
        coerced = pd.to_numeric(series, errors="coerce")
        bad = coerced.isna() & series.notna()
        if bad.any():
            result.errors.append(
                f"Column '{spec.name}': {bad.sum()} value(s) are not numeric "
                f"(e.g. row {series[bad].index[0]}: '{series[bad].iloc[0]}')."
            )
        else:
            if not spec.allow_negative and (coerced < 0).any():
                n = (coerced < 0).sum()
                result.errors.append(
                    f"Column '{spec.name}': {n} negative value(s) found; negatives not allowed."
                )
            if not spec.allow_zero and (coerced == 0).any():
                n = (coerced == 0).sum()
                result.errors.append(
                    f"Column '{spec.name}': {n} zero value(s) found; zero not allowed "
                    f"(would cause division errors downstream, e.g. Avg_Price)."
                )

    elif spec.dtype == "string":
        empty = series.isna() | (series.astype(str).str.strip() == "")
        if empty.any():
            result.warnings.append(
                f"Column '{spec.name}': {empty.sum()} empty value(s) will be filled as 'Unknown'."
            )


def _check_nulls(df: pd.DataFrame, result: ValidationResult) -> None:
    for spec in REQUIRED_COLUMNS:
        if spec.name not in df.columns:
            continue
        n_null = df[spec.name].isna().sum()
        if n_null > 0 and spec.dtype != "string":
            result.warnings.append(
                f"Column '{spec.name}': {n_null} null value(s) present."
            )


def validate_dataframe(df: pd.DataFrame) -> ValidationResult:
    """
    Run the full validation suite against a raw DataFrame.
    Returns a ValidationResult; does NOT raise, so callers (e.g. Streamlit)
    can render the report directly to the user.
    """
    result = ValidationResult(is_valid=True, row_count=len(df))

    if df.empty:
        result.errors.append("The uploaded file contains no rows.")
        result.is_valid = False
        return result

    _check_columns_present(df, result)

    # Only run dtype checks on columns that actually exist
    if not result.errors:
        for spec in REQUIRED_COLUMNS:
            _check_dtype(df, spec, result)
        _check_nulls(df, result)

    result.is_valid = len(result.errors) == 0
    return result


def load_and_validate(filepath: str | Path) -> tuple[pd.DataFrame, ValidationResult]:
    """
    Load a CSV or Excel file and validate it in one step.
    Supported extensions: .csv, .xlsx, .xls
    """
    filepath = Path(filepath)
    if filepath.suffix.lower() == ".csv":
        df = pd.read_csv(filepath)
    elif filepath.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file type: {filepath.suffix}")

    result = validate_dataframe(df)
    return df, result
