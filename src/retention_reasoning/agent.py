"""Main Retention Reasoning Agent using LangGraph."""

from typing import Any, TypedDict

import pandas as pd
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, END
from loguru import logger

from .models.opportunity import Opportunity
from .models.reasoning import ReasoningSession
from .nodes import (
    HypothesisGeneratorNode,
    CausalTesterNode,
    ConfounderAnalyzerNode,
    LeverEstimatorNode,
    ExplanationGeneratorNode,
)


class ReasoningState(TypedDict):
    """State for the retention reasoning graph."""

    # Input
    opportunity: Opportunity
    session_id: str
    business_context: str | None
    data: pd.DataFrame | None

    # Intermediate
    hypotheses: list[Any]
    hypotheses_count: int
    validated_hypotheses: list[Any]
    validated_count: int
    validated_causes: list[str]
    actionable_levers: list[str]
    recommended_levers: list[str]

    # Output
    explanation: str
    confidence_score: float

    # Error handling
    error: str | None


class RetentionReasoningAgent:
    """Main agent that orchestrates retention causal reasoning."""

    def __init__(
        self,
        llm: BaseChatModel,
        available_features: list[str],
        data_loader: Any = None,
    ):
        """Initialize the retention reasoning agent.

        Args:
            llm: Language model for hypothesis generation and explanation
            available_features: List of available features in the dataset
            data_loader: Optional data loader for BigQuery access
        """
        self.llm = llm
        self.available_features = available_features
        self.data_loader = data_loader

        # Initialize nodes
        self.hypothesis_generator = HypothesisGeneratorNode(
            llm=llm,
            available_features=available_features,
        )
        self.causal_tester = CausalTesterNode(data_loader=data_loader)
        self.confounder_analyzer = ConfounderAnalyzerNode()
        self.lever_estimator = LeverEstimatorNode()
        self.explanation_generator = ExplanationGeneratorNode(llm=llm)

        # Build graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph reasoning pipeline.

        Returns:
            Compiled LangGraph
        """
        workflow = StateGraph(ReasoningState)

        # Add nodes
        workflow.add_node("generate_hypotheses", self.hypothesis_generator)
        workflow.add_node("test_hypotheses", self.causal_tester)
        workflow.add_node("analyze_confounders", self.confounder_analyzer)
        workflow.add_node("estimate_levers", self.lever_estimator)
        workflow.add_node("generate_explanation", self.explanation_generator)

        # Define edges
        workflow.set_entry_point("generate_hypotheses")
        workflow.add_edge("generate_hypotheses", "test_hypotheses")
        workflow.add_edge("test_hypotheses", "analyze_confounders")
        workflow.add_edge("analyze_confounders", "estimate_levers")
        workflow.add_edge("estimate_levers", "generate_explanation")
        workflow.add_edge("generate_explanation", END)

        # Compile
        return workflow.compile()

    async def analyze_opportunity(
        self,
        opportunity: Opportunity,
        data: pd.DataFrame,
        business_context: str | None = None,
    ) -> ReasoningSession:
        """Analyze a retention opportunity to identify causal factors.

        Args:
            opportunity: The retention opportunity to analyze
            data: Customer data for analysis
            business_context: Optional business context

        Returns:
            ReasoningSession with complete analysis
        """
        logger.info(f"Starting reasoning analysis for opportunity: {opportunity.opportunity_id}")

        # Create session
        session = ReasoningSession(opportunity_id=opportunity.opportunity_id)

        # Initialize state
        initial_state: ReasoningState = {
            "opportunity": opportunity,
            "session_id": session.session_id,
            "business_context": business_context,
            "data": data,
            "hypotheses": [],
            "hypotheses_count": 0,
            "validated_hypotheses": [],
            "validated_count": 0,
            "validated_causes": [],
            "actionable_levers": [],
            "recommended_levers": [],
            "explanation": "",
            "confidence_score": 0.0,
            "error": None,
        }

        try:
            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)

            # Update session with results
            session.hypotheses = final_state.get("hypotheses", [])
            session.hypotheses_count = len(session.hypotheses)
            session.validated_causes = final_state.get("validated_causes", [])
            session.confidence_score = self._calculate_confidence(final_state)

            # TODO: Convert actionable_levers to Lever objects
            # For now, store as simple list
            session.agent_state = {
                "actionable_levers": final_state.get("actionable_levers", []),
                "explanation": final_state.get("explanation", ""),
            }

            session.mark_completed()
            logger.info(
                f"Analysis complete: {session.validated_hypotheses_count} validated hypotheses"
            )

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            session.mark_failed(str(e))

        return session

    def analyze_opportunity_sync(
        self,
        opportunity: Opportunity,
        data: pd.DataFrame,
        business_context: str | None = None,
    ) -> ReasoningSession:
        """Synchronous version of analyze_opportunity.

        Args:
            opportunity: The retention opportunity to analyze
            data: Customer data for analysis
            business_context: Optional business context

        Returns:
            ReasoningSession with complete analysis
        """
        import asyncio

        return asyncio.run(
            self.analyze_opportunity(opportunity, data, business_context)
        )

    def _calculate_confidence(self, state: ReasoningState) -> float:
        """Calculate overall confidence score.

        Args:
            state: Final graph state

        Returns:
            Confidence score (0-1)
        """
        validated_count = state.get("validated_count", 0)
        hypotheses_count = state.get("hypotheses_count", 1)

        # Base confidence on validation rate
        validation_rate = validated_count / max(hypotheses_count, 1)

        # TODO: Factor in test confidence scores
        return min(validation_rate, 1.0)

    def get_graph_visualization(self) -> str:
        """Get a visualization of the reasoning graph.

        Returns:
            Mermaid diagram string
        """
        return """
        graph TD
            A[Start] --> B[Generate Hypotheses]
            B --> C[Test Hypotheses]
            C --> D[Analyze Confounders]
            D --> E[Estimate Levers]
            E --> F[Generate Explanation]
            F --> G[End]
        """
