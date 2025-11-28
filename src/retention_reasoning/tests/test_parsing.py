import pandas as pd

from retention_reasoning.nodes.causal_tester import CausalTesterNode
from retention_reasoning.nodes.hypothesis_generator import HypothesisGeneratorNode


class _FakeLLM:
    """Minimal stub; we only need the interface present."""

    async def ainvoke(self, messages):  # pragma: no cover - unused in tests
        return type("Resp", (), {"content": ""})


def test_alias_resolution_maps_common_variants():
    gen = HypothesisGeneratorNode(
        llm=_FakeLLM(),
        available_features=["first_delivery_days", "order_value"],
    )
    assert gen._resolve_cause_feature("first_order_day > 3") == "first_delivery_days"
    assert gen._resolve_cause_feature("average_order_value < 50") == "order_value"
    assert gen._resolve_cause_feature("order_frequency < 2") == "order_value"


def test_treatment_parser_handles_and_or():
    node = CausalTesterNode()
    df = pd.DataFrame(
        {
            "cat": ["a", "b", "a", "b"],
            "val": [1, 10, 5, 8],
        }
    )

    or_series = node._build_treatment_series('cat = "a" OR cat = "b"', df)
    assert or_series.tolist() == [1, 1, 1, 1]

    and_series = node._build_treatment_series('cat = "b" AND val > 9', df)
    assert and_series.tolist() == [0, 1, 0, 0]


def test_treatment_parser_handles_not():
    node = CausalTesterNode()
    df = pd.DataFrame({"cat": ["a", "b", "a", "b"]})
    not_series = node._build_treatment_series('NOT cat = "a"', df)
    assert not_series.tolist() == [0, 1, 0, 1]


def test_treatment_parser_handles_parentheses_and_in_list():
    node = CausalTesterNode()
    df = pd.DataFrame(
        {
            "cat": ["a", "b", "c", "d"],
            "val": [1, 2, 3, 4],
        }
    )
    paren_series = node._build_treatment_series('(cat = "a" OR cat = "b") AND val > 1', df)
    assert paren_series.tolist() == [0, 1, 0, 0]

    in_series = node._build_treatment_series('cat IN ("a","c")', df)
    assert in_series.tolist() == [1, 0, 1, 0]
