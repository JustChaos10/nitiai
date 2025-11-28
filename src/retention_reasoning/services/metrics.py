"""Metrics computation service for retention analysis."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger


class MetricsService:
    """Compute and track retention metrics."""

    # Standard retention metrics
    STANDARD_METRICS = [
        "churn_rate_30d",
        "avg_order_value",
        "ltv_cac_ratio",
        "return_rate",
        "discount_revenue_share",
        "active_users_30d",
        "repeat_purchase_rate",
        "customer_lifetime_value",
    ]

    def __init__(self):
        """Initialize metrics service."""
        pass

    def compute_metrics(
        self, 
        customers: pd.DataFrame, 
        brand_id: str | None = None
    ) -> dict[str, float]:
        """Compute current metric values from customer data.
        
        Args:
            customers: Customer DataFrame
            brand_id: Optional brand filter
            
        Returns:
            Dictionary of metric name to current value
        """
        if customers.empty:
            return {}
        
        # Filter by brand if specified
        df = customers
        if brand_id and "brand_id" in df.columns:
            df = df[df["brand_id"] == brand_id]
        
        if df.empty:
            return {}
        
        metrics = {}
        
        # Churn rate
        if "churn_flag" in df.columns:
            churn_col = df["churn_flag"]
            if churn_col.dtype == bool:
                metrics["churn_rate_30d"] = churn_col.mean()
            else:
                metrics["churn_rate_30d"] = (churn_col == True).mean()
        
        # Average order value
        if "avg_order_value" in df.columns:
            metrics["avg_order_value"] = df["avg_order_value"].mean()
        
        # LTV/CAC ratio
        if "ltv_cac_ratio" in df.columns:
            metrics["ltv_cac_ratio"] = df["ltv_cac_ratio"].mean()
        elif "ltv_12m" in df.columns and "cac" in df.columns:
            valid = df["cac"] > 0
            if valid.any():
                metrics["ltv_cac_ratio"] = (df.loc[valid, "ltv_12m"] / df.loc[valid, "cac"]).mean()
        
        # Return rate
        if "return_rate" in df.columns:
            metrics["return_rate"] = df["return_rate"].mean()
        
        # Discount dependency
        if "discount_orders_share" in df.columns:
            metrics["discount_revenue_share"] = df["discount_orders_share"].mean()
        
        # Active users
        if "active_30d" in df.columns:
            active_col = df["active_30d"]
            if active_col.dtype == bool:
                metrics["active_users_30d"] = active_col.sum()
            else:
                metrics["active_users_30d"] = (active_col == True).sum()
        
        # Repeat purchase rate
        if "total_orders" in df.columns:
            metrics["repeat_purchase_rate"] = (df["total_orders"] > 1).mean()
        
        # Customer lifetime value
        if "ltv_12m" in df.columns:
            metrics["customer_lifetime_value"] = df["ltv_12m"].mean()
        
        # Total revenue
        if "total_revenue" in df.columns:
            metrics["total_revenue"] = df["total_revenue"].sum()
        
        # Customer count
        metrics["total_customers"] = len(df)
        
        logger.info(f"Computed {len(metrics)} metrics for brand={brand_id}")
        
        # Convert numpy types to native Python types for JSON serialization
        def to_native(v):
            if isinstance(v, (np.integer,)):
                return int(v)
            elif isinstance(v, (np.floating,)):
                return float(v)
            elif isinstance(v, np.bool_):
                return bool(v)
            return v
        
        return {k: to_native(v) for k, v in metrics.items()}

    def compute_daily_trends(
        self,
        metrics_daily: pd.DataFrame,
        metric_name: str,
        brand_id: str | None = None,
        days: int = 30,
    ) -> dict[str, float]:
        """Get daily values for a metric.
        
        Args:
            metrics_daily: Daily metrics DataFrame
            metric_name: Name of metric to retrieve
            brand_id: Optional brand filter
            days: Number of days to include
            
        Returns:
            Dictionary mapping date string to value
            Example: {"2025-11-01": 0.2, "2025-11-02": 0.21, ...}
        """
        if metrics_daily.empty:
            return {}
        
        df = metrics_daily.copy()
        
        # Filter by metric name
        if "metric_name" in df.columns:
            df = df[df["metric_name"] == metric_name]
        
        if df.empty:
            return {}
        
        # Filter by brand if specified
        if brand_id and "brand_id" in df.columns:
            df = df[df["brand_id"] == brand_id]
        
        if df.empty:
            return {}
        
        # Ensure date column
        date_col = None
        for col in ["date", "snapshot_date", "metric_date"]:
            if col in df.columns:
                date_col = col
                break
        
        if date_col is None:
            logger.warning("No date column found in metrics_daily")
            return {}
        
        # Parse dates if needed
        if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
            df[date_col] = pd.to_datetime(df[date_col], format="mixed")
        
        # Sort by date and take last N days
        df = df.sort_values(date_col, ascending=False).head(days)
        
        # Build result dictionary
        result = {}
        for _, row in df.iterrows():
            date_str = row[date_col].strftime("%Y-%m-%d")
            result[date_str] = float(row["value"])
        
        # Sort by date
        result = dict(sorted(result.items()))
        
        logger.info(f"Retrieved {len(result)} daily values for {metric_name}")
        return result

    def compute_all_trends(
        self,
        metrics_daily: pd.DataFrame,
        brand_id: str | None = None,
        days: int = 30,
    ) -> dict[str, dict[str, float]]:
        """Get daily trends for all available metrics.
        
        Args:
            metrics_daily: Daily metrics DataFrame
            brand_id: Optional brand filter
            days: Number of days to include
            
        Returns:
            Dictionary mapping metric name to daily values
        """
        if metrics_daily.empty or "metric_name" not in metrics_daily.columns:
            return {}
        
        result = {}
        for metric_name in metrics_daily["metric_name"].unique():
            trend = self.compute_daily_trends(
                metrics_daily, 
                metric_name, 
                brand_id, 
                days
            )
            if trend:
                result[metric_name] = trend
        
        return result

    def compute_metrics_from_events(
        self,
        events: pd.DataFrame,
        customers: pd.DataFrame,
        date_range: tuple[datetime, datetime] | None = None,
    ) -> dict[str, float]:
        """Compute metrics from raw event data.
        
        Args:
            events: Events DataFrame
            customers: Customers DataFrame
            date_range: Optional (start, end) date filter
            
        Returns:
            Computed metrics
        """
        metrics = {}
        
        if events.empty:
            return metrics
        
        df = events.copy()
        
        # Filter by date if specified
        if date_range and "event_time" in df.columns:
            start, end = date_range
            df = df[(df["event_time"] >= start) & (df["event_time"] <= end)]
        
        # Event type counts
        if "event_type" in df.columns:
            type_counts = df["event_type"].value_counts().to_dict()
            metrics["total_sessions"] = type_counts.get("session", 0)
            metrics["total_purchases"] = type_counts.get("purchase", 0)
            metrics["total_signups"] = type_counts.get("signup", 0)
        
        # Conversion rate (signups to purchases)
        if metrics.get("total_signups", 0) > 0:
            purchasing_customers = df[df["event_type"] == "purchase"]["customer_id"].nunique()
            total_customers = df["customer_id"].nunique()
            metrics["conversion_rate"] = purchasing_customers / total_customers if total_customers > 0 else 0
        
        # Average sessions per customer
        if "customer_id" in df.columns and "event_type" in df.columns:
            sessions = df[df["event_type"] == "session"]
            if not sessions.empty:
                metrics["avg_sessions_per_customer"] = len(sessions) / sessions["customer_id"].nunique()
        
        return metrics

    def detect_metric_changes(
        self,
        current: dict[str, float],
        baseline: dict[str, float],
    ) -> list[dict[str, Any]]:
        """Detect significant changes between current and baseline metrics.
        
        Args:
            current: Current metric values
            baseline: Baseline metric values
            
        Returns:
            List of detected changes with magnitude
        """
        changes = []
        
        for metric, current_val in current.items():
            if metric not in baseline:
                continue
            
            baseline_val = baseline[metric]
            if baseline_val == 0:
                continue
            
            change_pct = (current_val - baseline_val) / baseline_val * 100
            
            # Flag significant changes (>10%)
            if abs(change_pct) > 10:
                changes.append({
                    "metric": metric,
                    "baseline": baseline_val,
                    "current": current_val,
                    "change_pct": change_pct,
                    "direction": "increase" if change_pct > 0 else "decrease",
                    "severity": "high" if abs(change_pct) > 25 else "medium",
                })
        
        # Sort by absolute change
        changes.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
        
        return changes

