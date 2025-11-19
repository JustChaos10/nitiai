"""Causal inference engine using DoWhy framework."""

import warnings
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd

from ..models.hypothesis import CausalStructure, Hypothesis

try:
    from dowhy import CausalModel
    DOWHY_AVAILABLE = True
except ImportError:
    DOWHY_AVAILABLE = False
    warnings.warn("DoWhy not available. Install with: pip install dowhy")


class CausalInferenceEngine:
    """Advanced causal inference using DoWhy framework."""

    def __init__(self):
        """Initialize causal inference engine."""
        if not DOWHY_AVAILABLE:
            raise ImportError("DoWhy is required. Install with: pip install dowhy")

    def build_causal_dag(
        self,
        hypothesis: Hypothesis,
        data: pd.DataFrame,
    ) -> tuple[nx.DiGraph, dict[str, float]]:
        """Build a causal DAG (Directed Acyclic Graph) for the hypothesis.

        Args:
            hypothesis: Hypothesis to analyze
            data: Data for analysis

        Returns:
            Tuple of (DAG, edge_strengths)
        """
        G = nx.DiGraph()

        # Add nodes
        nodes = [hypothesis.cause, hypothesis.effect]
        nodes.extend(hypothesis.confounders)
        nodes.extend(hypothesis.mediators)
        nodes.extend(hypothesis.moderators)

        for node in set(nodes):
            G.add_node(node)

        # Add edges based on hypothesis structure
        edge_strengths = {}

        # Main causal edge
        G.add_edge(hypothesis.cause, hypothesis.effect)
        edge_strengths[(hypothesis.cause, hypothesis.effect)] = self._estimate_edge_strength(
            data, hypothesis.cause, hypothesis.effect
        )

        # Confounder edges (affect both treatment and outcome)
        for confounder in hypothesis.confounders:
            if confounder in data.columns:
                G.add_edge(confounder, hypothesis.cause)
                G.add_edge(confounder, hypothesis.effect)
                edge_strengths[(confounder, hypothesis.cause)] = self._estimate_edge_strength(
                    data, confounder, hypothesis.cause
                )
                edge_strengths[(confounder, hypothesis.effect)] = self._estimate_edge_strength(
                    data, confounder, hypothesis.effect
                )

        # Mediator edges (cause → mediator → effect)
        for mediator in hypothesis.mediators:
            if mediator in data.columns:
                G.add_edge(hypothesis.cause, mediator)
                G.add_edge(mediator, hypothesis.effect)
                edge_strengths[(hypothesis.cause, mediator)] = self._estimate_edge_strength(
                    data, hypothesis.cause, mediator
                )
                edge_strengths[(mediator, hypothesis.effect)] = self._estimate_edge_strength(
                    data, mediator, hypothesis.effect
                )

        return G, edge_strengths

    def analyze_causal_structure(
        self,
        hypothesis: Hypothesis,
        data: pd.DataFrame,
    ) -> CausalStructure:
        """Analyze the full causal structure including mediation and confounding.

        Args:
            hypothesis: Hypothesis to analyze
            data: Data for analysis

        Returns:
            CausalStructure with detailed breakdown
        """
        # Build DAG
        dag, edge_strengths = self.build_causal_dag(hypothesis, data)

        # Estimate direct effect (controlling for mediators)
        direct_effect = self._estimate_direct_effect(
            data, hypothesis.cause, hypothesis.effect, hypothesis.mediators
        )

        # Estimate indirect effect (through mediators)
        indirect_effect = self._estimate_indirect_effect(
            data, hypothesis.cause, hypothesis.effect, hypothesis.mediators
        )

        # Total effect
        total_effect = direct_effect + indirect_effect

        # Determine true cause vs proximate cause
        if abs(indirect_effect) > abs(direct_effect) * 2:
            # Indirect effect dominates
            true_cause = hypothesis.mediators[0] if hypothesis.mediators else hypothesis.cause
            actionable_lever = true_cause
        else:
            true_cause = hypothesis.cause
            actionable_lever = hypothesis.cause

        # Build node and edge representations
        nodes = [
            {"id": node, "label": node, "type": self._classify_node(node, hypothesis)}
            for node in dag.nodes()
        ]

        edges = [
            {
                "source": u,
                "target": v,
                "strength": edge_strengths.get((u, v), 0.0),
                "label": f"{edge_strengths.get((u, v), 0.0):.2f}",
            }
            for u, v in dag.edges()
        ]

        # Confidence in structure
        structure_confidence = self._assess_structure_confidence(
            dag, edge_strengths, len(data)
        )

        return CausalStructure(
            hypothesis_id=hypothesis.hypothesis_id,
            direct_effect=direct_effect,
            indirect_effect=indirect_effect,
            total_effect=total_effect,
            mediators=hypothesis.mediators,
            confounders=hypothesis.confounders,
            colliders=[],  # TODO: Detect colliders
            true_cause=true_cause,
            proximate_cause=hypothesis.cause,
            actionable_lever=actionable_lever,
            nodes=nodes,
            edges=edges,
            structure_confidence=structure_confidence,
        )

    def _estimate_edge_strength(
        self, data: pd.DataFrame, source: str, target: str
    ) -> float:
        """Estimate the strength of a causal edge using correlation.

        Args:
            data: Data
            source: Source variable
            target: Target variable

        Returns:
            Edge strength (correlation coefficient)
        """
        if source not in data.columns or target not in data.columns:
            return 0.0

        # Handle missing data
        valid_data = data[[source, target]].dropna()
        if len(valid_data) < 10:
            return 0.0

        # Calculate correlation
        try:
            corr = valid_data[source].corr(valid_data[target])
            return corr if not np.isnan(corr) else 0.0
        except Exception:
            return 0.0

    def _estimate_direct_effect(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        mediators: list[str],
    ) -> float:
        """Estimate direct causal effect (controlling for mediators).

        Args:
            data: Data
            treatment: Treatment variable
            outcome: Outcome variable
            mediators: Mediating variables

        Returns:
            Direct effect estimate
        """
        from sklearn.linear_model import LinearRegression

        # Prepare data
        valid_mediators = [m for m in mediators if m in data.columns]
        if not valid_mediators:
            # No mediators, direct effect = total effect
            return self._estimate_edge_strength(data, treatment, outcome)

        cols = [treatment, outcome] + valid_mediators
        valid_data = data[cols].dropna()

        if len(valid_data) < 20:
            return 0.0

        # Fit regression: outcome ~ treatment + mediators
        X = valid_data[[treatment] + valid_mediators]
        y = valid_data[outcome]

        try:
            model = LinearRegression()
            model.fit(X, y)
            # Direct effect is the coefficient on treatment
            return model.coef_[0]
        except Exception:
            return 0.0

    def _estimate_indirect_effect(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        mediators: list[str],
    ) -> float:
        """Estimate indirect causal effect (through mediators).

        Args:
            data: Data
            treatment: Treatment variable
            outcome: Outcome variable
            mediators: Mediating variables

        Returns:
            Indirect effect estimate
        """
        from sklearn.linear_model import LinearRegression

        valid_mediators = [m for m in mediators if m in data.columns]
        if not valid_mediators:
            return 0.0

        # For simplicity, estimate indirect effect for first mediator
        mediator = valid_mediators[0]
        cols = [treatment, mediator, outcome]
        valid_data = data[cols].dropna()

        if len(valid_data) < 20:
            return 0.0

        try:
            # Path 1: treatment → mediator
            X1 = valid_data[[treatment]]
            y1 = valid_data[mediator]
            model1 = LinearRegression()
            model1.fit(X1, y1)
            a_path = model1.coef_[0]

            # Path 2: mediator → outcome (controlling for treatment)
            X2 = valid_data[[treatment, mediator]]
            y2 = valid_data[outcome]
            model2 = LinearRegression()
            model2.fit(X2, y2)
            b_path = model2.coef_[1]

            # Indirect effect = a * b
            return a_path * b_path

        except Exception:
            return 0.0

    def _classify_node(self, node: str, hypothesis: Hypothesis) -> str:
        """Classify a node's role in the causal graph.

        Args:
            node: Node name
            hypothesis: Hypothesis

        Returns:
            Node type (treatment, outcome, confounder, mediator, moderator)
        """
        if node == hypothesis.cause:
            return "treatment"
        elif node == hypothesis.effect:
            return "outcome"
        elif node in hypothesis.confounders:
            return "confounder"
        elif node in hypothesis.mediators:
            return "mediator"
        elif node in hypothesis.moderators:
            return "moderator"
        else:
            return "unknown"

    def _assess_structure_confidence(
        self, dag: nx.DiGraph, edge_strengths: dict[tuple[str, str], float], sample_size: int
    ) -> float:
        """Assess confidence in the causal structure.

        Args:
            dag: Causal DAG
            edge_strengths: Edge strength estimates
            sample_size: Sample size

        Returns:
            Confidence score (0-1)
        """
        # Base confidence on sample size
        size_confidence = min(sample_size / 500, 1.0)

        # Base confidence on edge strengths (stronger edges = higher confidence)
        avg_strength = np.mean([abs(s) for s in edge_strengths.values()]) if edge_strengths else 0
        strength_confidence = min(avg_strength * 2, 1.0)

        # Combine
        return (size_confidence * 0.6 + strength_confidence * 0.4)

    def detect_confounders(
        self,
        data: pd.DataFrame,
        treatment: str,
        outcome: str,
        candidate_confounders: list[str],
        threshold: float = 0.1,
    ) -> list[str]:
        """Detect confounding variables that affect both treatment and outcome.

        Args:
            data: Data
            treatment: Treatment variable
            outcome: Outcome variable
            candidate_confounders: Candidate confounding variables
            threshold: Correlation threshold for detection

        Returns:
            List of detected confounders
        """
        confounders = []

        for candidate in candidate_confounders:
            if candidate not in data.columns:
                continue

            # Check if candidate correlates with both treatment and outcome
            corr_treatment = abs(data[[candidate, treatment]].dropna().corr().iloc[0, 1])
            corr_outcome = abs(data[[candidate, outcome]].dropna().corr().iloc[0, 1])

            if corr_treatment > threshold and corr_outcome > threshold:
                confounders.append(candidate)

        return confounders

    def export_graph_visualization(self, dag: nx.DiGraph, edge_strengths: dict) -> dict[str, Any]:
        """Export graph data for visualization (e.g., for Crayon/Thesys frontend).

        Args:
            dag: Causal DAG
            edge_strengths: Edge strengths

        Returns:
            Visualization data
        """
        return {
            "nodes": [
                {
                    "id": node,
                    "label": node,
                }
                for node in dag.nodes()
            ],
            "edges": [
                {
                    "source": u,
                    "target": v,
                    "weight": edge_strengths.get((u, v), 0.0),
                }
                for u, v in dag.edges()
            ],
        }
