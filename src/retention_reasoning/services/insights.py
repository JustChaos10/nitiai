"""Insights generation service for retention analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger


def _to_native(value: Any) -> Any:
    """Convert numpy types to native Python types for JSON serialization."""
    if isinstance(value, (np.integer,)):
        return int(value)
    elif isinstance(value, (np.floating,)):
        return float(value)
    elif isinstance(value, np.bool_):
        return bool(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    return value


def _clean_insight(insight: dict[str, Any]) -> dict[str, Any]:
    """Convert all numpy values in an insight dict to native types."""
    return {k: _to_native(v) for k, v in insight.items()}


class InsightsService:
    """Generate insights from metrics and features."""

    # Thresholds for anomaly detection
    SPIKE_THRESHOLD = 2.0  # Standard deviations
    DIP_THRESHOLD = -2.0
    TREND_WINDOW = 7  # Days for trend calculation

    def __init__(self):
        """Initialize insights service."""
        pass

    def generate_insights(
        self,
        metrics: dict[str, float],
        trends: dict[str, dict[str, float]],
        customers: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """Generate all insights from data.
        
        Args:
            metrics: Current metric values
            trends: Daily metric trends
            customers: Customer DataFrame
            
        Returns:
            List of insight dictionaries
        """
        insights = []
        
        # Current state insights
        insights.extend(self._analyze_current_metrics(metrics))
        
        # Trend insights
        insights.extend(self._analyze_trends(trends))
        
        # Anomaly insights
        insights.extend(self._detect_anomalies(trends))
        
        # Segment insights
        if not customers.empty:
            insights.extend(self._analyze_segments(customers, metrics))
        
        # Prioritize insights
        insights = self._prioritize_insights(insights)
        
        # Convert numpy types to native Python types for JSON serialization
        insights = [_clean_insight(i) for i in insights]
        
        logger.info(f"Generated {len(insights)} insights")
        return insights

    def _analyze_current_metrics(
        self, 
        metrics: dict[str, float]
    ) -> list[dict[str, Any]]:
        """Analyze current metric values.
        
        Args:
            metrics: Current metric values
            
        Returns:
            List of metric state insights
        """
        insights = []
        
        # Churn rate insights
        churn = metrics.get("churn_rate_30d")
        if churn is not None:
            if churn > 0.25:
                insights.append({
                    "type": "metric_state",
                    "category": "churn",
                    "severity": "high",
                    "metric": "churn_rate_30d",
                    "value": churn,
                    "message": f"High churn rate: {churn:.1%} of customers churned in last 30 days",
                    "recommendation": "Investigate top churn drivers and implement retention campaigns",
                })
            elif churn > 0.15:
                insights.append({
                    "type": "metric_state",
                    "category": "churn",
                    "severity": "medium",
                    "metric": "churn_rate_30d",
                    "value": churn,
                    "message": f"Elevated churn rate: {churn:.1%} of customers churned",
                    "recommendation": "Monitor churn drivers and proactive outreach",
                })
        
        # LTV/CAC insights
        ltv_cac = metrics.get("ltv_cac_ratio")
        if ltv_cac is not None:
            if ltv_cac < 3.0:
                insights.append({
                    "type": "metric_state",
                    "category": "unit_economics",
                    "severity": "high" if ltv_cac < 2.0 else "medium",
                    "metric": "ltv_cac_ratio",
                    "value": ltv_cac,
                    "message": f"Low LTV/CAC ratio: {ltv_cac:.1f}x (target: 3x+)",
                    "recommendation": "Focus on increasing customer lifetime value or reducing acquisition costs",
                })
        
        # Return rate insights
        return_rate = metrics.get("return_rate")
        if return_rate is not None and return_rate > 0.15:
            insights.append({
                "type": "metric_state",
                "category": "quality",
                "severity": "medium",
                "metric": "return_rate",
                "value": return_rate,
                "message": f"High return rate: {return_rate:.1%}",
                "recommendation": "Review product quality and customer expectations alignment",
            })
        
        # Discount dependency insights
        discount_share = metrics.get("discount_revenue_share")
        if discount_share is not None and discount_share > 0.4:
            insights.append({
                "type": "metric_state",
                "category": "pricing",
                "severity": "medium",
                "metric": "discount_revenue_share",
                "value": discount_share,
                "message": f"High discount dependency: {discount_share:.1%} of orders use discounts",
                "recommendation": "Reduce discount reliance to protect margins",
            })
        
        return insights

    def _analyze_trends(
        self, 
        trends: dict[str, dict[str, float]]
    ) -> list[dict[str, Any]]:
        """Analyze metric trends over time.
        
        Args:
            trends: Dictionary of metric name to daily values
            
        Returns:
            List of trend insights
        """
        insights = []
        
        for metric_name, daily_values in trends.items():
            if len(daily_values) < 7:
                continue
            
            # Convert to sorted list of values
            sorted_dates = sorted(daily_values.keys())
            values = [daily_values[d] for d in sorted_dates]
            
            # Calculate trend direction
            recent_values = values[-7:]
            older_values = values[-14:-7] if len(values) >= 14 else values[:7]
            
            if not older_values:
                continue
            
            recent_avg = np.mean(recent_values)
            older_avg = np.mean(older_values)
            
            if older_avg == 0:
                continue
            
            change_pct = (recent_avg - older_avg) / older_avg * 100
            
            # Flag significant trends
            if abs(change_pct) > 15:
                direction = "increasing" if change_pct > 0 else "decreasing"
                
                # Determine if trend is good or bad
                is_negative = False
                if "churn" in metric_name.lower() and change_pct > 0:
                    is_negative = True
                elif "ltv" in metric_name.lower() and change_pct < 0:
                    is_negative = True
                elif "active" in metric_name.lower() and change_pct < 0:
                    is_negative = True
                
                insights.append({
                    "type": "trend",
                    "category": "trend_analysis",
                    "severity": "high" if abs(change_pct) > 25 else "medium",
                    "metric": metric_name,
                    "direction": direction,
                    "change_pct": change_pct,
                    "recent_avg": recent_avg,
                    "older_avg": older_avg,
                    "is_negative": is_negative,
                    "message": f"{metric_name} is {direction} by {abs(change_pct):.1f}% week-over-week",
                    "recommendation": self._get_trend_recommendation(metric_name, direction, is_negative),
                })
        
        return insights

    def _detect_anomalies(
        self, 
        trends: dict[str, dict[str, float]]
    ) -> list[dict[str, Any]]:
        """Detect anomalies (spikes/dips) in metric trends.
        
        Args:
            trends: Dictionary of metric name to daily values
            
        Returns:
            List of anomaly insights
        """
        insights = []
        
        for metric_name, daily_values in trends.items():
            if len(daily_values) < 14:
                continue
            
            # Convert to time series
            sorted_dates = sorted(daily_values.keys())
            values = np.array([daily_values[d] for d in sorted_dates])
            
            # Calculate z-scores
            mean_val = np.mean(values[:-7])  # Use older data as baseline
            std_val = np.std(values[:-7])
            
            if std_val == 0:
                continue
            
            # Check recent values for anomalies
            for i, date in enumerate(sorted_dates[-7:]):
                val = daily_values[date]
                z_score = (val - mean_val) / std_val
                
                if z_score > self.SPIKE_THRESHOLD:
                    insights.append({
                        "type": "anomaly",
                        "category": "spike",
                        "severity": "high",
                        "metric": metric_name,
                        "date": date,
                        "value": val,
                        "expected": mean_val,
                        "z_score": z_score,
                        "message": f"Spike detected in {metric_name} on {date}: {val:.4f} (expected: {mean_val:.4f})",
                        "recommendation": "Investigate recent changes that may have caused this spike",
                    })
                elif z_score < self.DIP_THRESHOLD:
                    insights.append({
                        "type": "anomaly",
                        "category": "dip",
                        "severity": "high",
                        "metric": metric_name,
                        "date": date,
                        "value": val,
                        "expected": mean_val,
                        "z_score": z_score,
                        "message": f"Dip detected in {metric_name} on {date}: {val:.4f} (expected: {mean_val:.4f})",
                        "recommendation": "Investigate recent changes that may have caused this drop",
                    })
        
        return insights

    def _analyze_segments(
        self,
        customers: pd.DataFrame,
        metrics: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Analyze customer segments for insights.
        
        Args:
            customers: Customer DataFrame
            metrics: Current metrics
            
        Returns:
            List of segment insights
        """
        insights = []
        
        if customers.empty:
            return insights
        
        # Lifecycle stage analysis
        if "lifecycle_stage" in customers.columns and "churn_flag" in customers.columns:
            stage_churn = customers.groupby("lifecycle_stage")["churn_flag"].mean()
            
            for stage, churn_rate in stage_churn.items():
                if churn_rate > 0.3:
                    count = (customers["lifecycle_stage"] == stage).sum()
                    insights.append({
                        "type": "segment",
                        "category": "lifecycle",
                        "severity": "high",
                        "segment": stage,
                        "metric": "churn_rate",
                        "value": churn_rate,
                        "count": count,
                        "message": f"High churn in {stage} segment: {churn_rate:.1%} ({count} customers)",
                        "recommendation": f"Create targeted retention campaign for {stage} customers",
                    })
        
        # Acquisition channel analysis
        if "acquisition_channel" in customers.columns and "churn_flag" in customers.columns:
            channel_churn = customers.groupby("acquisition_channel")["churn_flag"].mean()
            overall_churn = customers["churn_flag"].mean()
            
            for channel, churn_rate in channel_churn.items():
                if churn_rate > overall_churn * 1.5:  # 50% higher than average
                    count = (customers["acquisition_channel"] == channel).sum()
                    insights.append({
                        "type": "segment",
                        "category": "acquisition",
                        "severity": "medium",
                        "segment": channel,
                        "metric": "churn_rate",
                        "value": churn_rate,
                        "benchmark": overall_churn,
                        "count": count,
                        "message": f"High churn from {channel}: {churn_rate:.1%} vs {overall_churn:.1%} overall",
                        "recommendation": f"Review quality of {channel} acquisitions",
                    })
        
        # Region analysis
        if "region" in customers.columns and "ltv_12m" in customers.columns:
            region_ltv = customers.groupby("region")["ltv_12m"].mean()
            overall_ltv = customers["ltv_12m"].mean()
            
            for region, ltv in region_ltv.items():
                if ltv > overall_ltv * 1.3:  # 30% higher than average
                    count = (customers["region"] == region).sum()
                    insights.append({
                        "type": "segment",
                        "category": "geographic",
                        "severity": "info",
                        "segment": region,
                        "metric": "ltv_12m",
                        "value": ltv,
                        "benchmark": overall_ltv,
                        "count": count,
                        "message": f"High LTV in {region}: ${ltv:.2f} vs ${overall_ltv:.2f} overall",
                        "recommendation": f"Consider expanding acquisition in {region}",
                    })
        
        return insights

    def _get_trend_recommendation(
        self, 
        metric: str, 
        direction: str,
        is_negative: bool,
    ) -> str:
        """Get recommendation for a trend.
        
        Args:
            metric: Metric name
            direction: Trend direction
            is_negative: Whether trend is negative for business
            
        Returns:
            Recommendation string
        """
        if is_negative:
            if "churn" in metric.lower():
                return "Investigate root causes and implement retention interventions"
            elif "ltv" in metric.lower():
                return "Focus on increasing purchase frequency and order values"
            elif "active" in metric.lower():
                return "Launch re-engagement campaigns for inactive users"
            else:
                return "Analyze contributing factors and take corrective action"
        else:
            return "Monitor trend and identify successful factors to replicate"

    def _prioritize_insights(
        self, 
        insights: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Prioritize insights by severity and actionability.
        
        Args:
            insights: List of raw insights
            
        Returns:
            Sorted insights with priority scores
        """
        severity_scores = {"high": 3, "medium": 2, "low": 1, "info": 0}
        
        for insight in insights:
            # Calculate priority score
            severity = insight.get("severity", "medium")
            score = severity_scores.get(severity, 1)
            
            # Boost anomalies and negative trends
            if insight["type"] == "anomaly":
                score += 1
            if insight.get("is_negative"):
                score += 1
            
            insight["priority_score"] = score
        
        # Sort by priority
        insights.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        
        return insights

    def format_insights_for_llm(
        self, 
        insights: list[dict[str, Any]],
        max_insights: int = 10,
    ) -> str:
        """Format insights for LLM consumption.
        
        Args:
            insights: List of insights
            max_insights: Maximum number to include
            
        Returns:
            Formatted string for LLM prompt
        """
        if not insights:
            return "No significant insights detected."
        
        lines = ["## Current Insights\n"]
        
        for i, insight in enumerate(insights[:max_insights]):
            severity = insight.get("severity", "medium").upper()
            message = insight.get("message", "")
            recommendation = insight.get("recommendation", "")
            
            lines.append(f"{i+1}. [{severity}] {message}")
            if recommendation:
                lines.append(f"   → Recommendation: {recommendation}")
            lines.append("")
        
        return "\n".join(lines)

