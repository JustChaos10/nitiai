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