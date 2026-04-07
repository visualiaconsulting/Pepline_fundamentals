from typing import Iterable, List, Optional

import pandas as pd


def safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, float) and pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return str(value).strip().lower()


def contains_any(text: str, keywords: Iterable[str]) -> bool:
    clean_text = normalize_text(text)
    return any(normalize_text(keyword) in clean_text for keyword in keywords)


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def ensure_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    return df.copy()


def to_comma_list(values: List[str]) -> str:
    return ", ".join(values)
