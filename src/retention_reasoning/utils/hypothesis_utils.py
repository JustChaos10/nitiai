"""Helper utilities for working with hypothesis objects or dictionaries."""

from __future__ import annotations

from typing import Any

from ..models.hypothesis import Hypothesis


def hypothesis_to_dict(hypothesis: Any) -> dict[str, Any]:
    """Return a dict representation regardless of underlying object type."""

    if isinstance(hypothesis, dict):
        return hypothesis

    if isinstance(hypothesis, Hypothesis):
        return hypothesis.as_dict()

    if hasattr(hypothesis, "as_dict") and callable(hypothesis.as_dict):
        return hypothesis.as_dict()

    if hasattr(hypothesis, "model_dump") and callable(hypothesis.model_dump):
        return hypothesis.model_dump(mode="json")

    raise TypeError(
        f"Unsupported hypothesis representation: {type(hypothesis)!r}"
    )


def coerce_to_float(value: Any, default: float = 0.0) -> float:
    """Normalize numeric inputs (including enums/labels) into floats for formatting."""

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        normalized = value.strip().lower()
        label_map = {"low": 0.25, "medium": 0.5, "high": 0.75}
        if normalized in label_map:
            return label_map[normalized]
        try:
            return float(value)
        except ValueError:
            return default

    return default