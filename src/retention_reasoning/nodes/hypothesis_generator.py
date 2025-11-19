"""Hypothesis generation node using LLM."""

import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from loguru import logger

from ..models.hypothesis import Hypothesis, Likelihood, TestMethod
from ..models.opportunity import Opportunity
from ..prompts.hypothesis_generation import (
    HYPOTHESIS_GENERATION_SYSTEM_PROMPT,
    generate_hypothesis_prompt,
)


class HypothesisGeneratorNode:
    """Generates causal hypotheses using an LLM."""

    def __init__(
        self,
        llm: BaseChatModel,
        available_features: list[str],
        max_hypotheses: int = 10,
    ):
        """Initialize hypothesis generator.

        Args:
            llm: Language model for generation
            available_features: List of available features in the dataset
            max_hypotheses: Maximum number of hypotheses to generate
        """
        self.llm = llm
        self.available_features = available_features
        self.max_hypotheses = max_hypotheses

    async def generate(
        self,
        opportunity: Opportunity,
        session_id: str,
        business_context: str | None = None,
    ) -> list[Hypothesis]:
        """Generate hypotheses for the given opportunity.

        Args:
            opportunity: The retention opportunity to analyze
            session_id: ID of the reasoning session
            business_context: Optional business context

        Returns:
            List of generated hypotheses
        """
        logger.info(f"Generating hypotheses for opportunity: {opportunity.opportunity_id}")

        # Create prompt
        prompt = generate_hypothesis_prompt(
            opportunity_context=opportunity.to_context_string(),
            available_features=self.available_features,
            business_context=business_context,
        )

        # Call LLM
        messages = [
            SystemMessage(content=HYPOTHESIS_GENERATION_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            response_text = response.content

            # Parse JSON response
            hypotheses_data = self._parse_response(response_text)

            # Convert to Hypothesis objects
            hypotheses = []
            for i, hyp_data in enumerate(hypotheses_data.get("hypotheses", [])[:self.max_hypotheses]):
                try:
                    hypothesis = Hypothesis(
                        session_id=session_id,
                        cause=hyp_data["cause"],
                        effect=hyp_data.get("effect", opportunity.metric_name),
                        mechanism=hyp_data["mechanism"],
                        confounders=hyp_data.get("confounders", []),
                        mediators=hyp_data.get("mediators", []),
                        moderators=hyp_data.get("moderators", []),
                        test_methods=[
                            TestMethod(method) for method in hyp_data.get("test_methods", [])
                        ],
                        data_requirements=hyp_data.get("data_requirements", []),
                        likelihood=Likelihood(hyp_data.get("likelihood", "medium")),
                        rationale=hyp_data.get("rationale", ""),
                    )
                    hypotheses.append(hypothesis)
                    logger.info(f"Generated hypothesis {i+1}: {hypothesis.cause} → {hypothesis.effect}")

                except Exception as e:
                    logger.warning(f"Failed to parse hypothesis {i+1}: {e}")
                    continue

            logger.info(f"Generated {len(hypotheses)} valid hypotheses")
            return hypotheses

        except Exception as e:
            logger.error(f"Failed to generate hypotheses: {e}")
            return []

    def _parse_response(self, response_text: str) -> dict[str, Any]:
        """Parse JSON response from LLM.

        Args:
            response_text: Raw response text

        Returns:
            Parsed JSON object
        """
        # Try to extract JSON from markdown code blocks if present
        if "```json" in response_text:
            start = response_text.index("```json") + 7
            end = response_text.index("```", start)
            response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.index("```") + 3
            end = response_text.index("```", start)
            response_text = response_text[start:end].strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response text: {response_text[:500]}")
            return {"hypotheses": []}

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph node function (sync wrapper).

        Args:
            state: Graph state

        Returns:
            Updated state
        """
        import asyncio

        opportunity = state["opportunity"]
        session_id = state["session_id"]
        business_context = state.get("business_context")

        hypotheses = asyncio.run(
            self.generate(opportunity, session_id, business_context)
        )

        state["hypotheses"] = hypotheses
        state["hypotheses_count"] = len(hypotheses)

        return state
