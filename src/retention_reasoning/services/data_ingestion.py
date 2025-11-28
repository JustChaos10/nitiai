"""Data ingestion service for loading CSV/Excel files."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd
from loguru import logger


class DataIngestionService:
    """Load and merge data from CSV/Excel files."""

    EXPECTED_FILES = {
        "customers": ["retention_customers.csv", "shopify_retention_synthetic_dataset.csv"],
        "events": ["retention_events.csv"],
        "metrics_daily": ["retention_brand_metrics_daily.csv"],
    }

    def __init__(self, data_dir: str | Path = "data"):
        """Initialize with data directory path.
        
        Args:
            data_dir: Path to directory containing data files
        """
        self.data_dir = Path(data_dir)

    def load_from_files(self) -> dict[str, pd.DataFrame]:
        """Load all data files from the data directory.
        
        Returns:
            Dictionary with dataframes: customers, events, metrics_daily
        """
        data = {}
        
        # Load customers
        customers_path = self.data_dir / "retention_customers.csv"
        if customers_path.exists():
            data["customers"] = self._load_csv(customers_path)
            logger.info(f"Loaded {len(data['customers'])} customers from {customers_path}")
        else:
            # Try alternative
            alt_path = self.data_dir / "shopify_retention_synthetic_dataset.csv"
            if alt_path.exists():
                data["customers"] = self._load_csv(alt_path)
                logger.info(f"Loaded {len(data['customers'])} customers from {alt_path}")
            else:
                logger.warning("No customer data file found")
                data["customers"] = pd.DataFrame()
        
        # Load events
        events_path = self.data_dir / "retention_events.csv"
        if events_path.exists():
            data["events"] = self._load_csv(events_path)
            logger.info(f"Loaded {len(data['events'])} events from {events_path}")
        else:
            logger.warning("No events data file found")
            data["events"] = pd.DataFrame()
        
        # Load daily metrics
        metrics_path = self.data_dir / "retention_brand_metrics_daily.csv"
        if metrics_path.exists():
            data["metrics_daily"] = self._load_csv(metrics_path)
            logger.info(f"Loaded {len(data['metrics_daily'])} metric records from {metrics_path}")
        else:
            logger.warning("No daily metrics data file found")
            data["metrics_daily"] = pd.DataFrame()
        
        return data

    def _load_csv(self, path: Path) -> pd.DataFrame:
        """Load a CSV file with proper date parsing.
        
        Args:
            path: Path to CSV file
            
        Returns:
            Loaded DataFrame
        """
        df = pd.read_csv(path)
        
        # Parse date columns
        date_columns = [col for col in df.columns if any(
            keyword in col.lower() 
            for keyword in ["date", "time", "month", "snapshot"]
        )]
        
        for col in date_columns:
            try:
                df[col] = pd.to_datetime(df[col], format="mixed", dayfirst=False)
            except Exception:
                logger.debug(f"Could not parse {col} as datetime")
        
        return df

    def load_from_upload(
        self, 
        files: dict[str, BinaryIO | bytes]
    ) -> dict[str, pd.DataFrame]:
        """Load data from uploaded files.
        
        Args:
            files: Dictionary mapping file type to file content
                   Keys: 'customers', 'events', 'metrics_daily'
                   
        Returns:
            Dictionary with loaded DataFrames
        """
        data = {}
        
        for file_type, file_content in files.items():
            if file_content is None:
                continue
                
            try:
                # Handle bytes or file-like object
                if isinstance(file_content, bytes):
                    buffer = io.BytesIO(file_content)
                else:
                    buffer = file_content
                
                # Detect file type and load
                df = self._load_from_buffer(buffer, file_type)
                data[file_type] = df
                logger.info(f"Loaded {len(df)} rows for {file_type}")
                
            except Exception as e:
                logger.error(f"Failed to load {file_type}: {e}")
                data[file_type] = pd.DataFrame()
        
        return data

    def _load_from_buffer(
        self, 
        buffer: BinaryIO, 
        filename: str = ""
    ) -> pd.DataFrame:
        """Load DataFrame from a file buffer.
        
        Args:
            buffer: File buffer
            filename: Original filename for type detection
            
        Returns:
            Loaded DataFrame
        """
        # Try to read position
        try:
            buffer.seek(0)
        except Exception:
            pass
        
        # Detect file type
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            return pd.read_excel(buffer)
        else:
            # Default to CSV
            return pd.read_csv(buffer)

    def merge_customer_events(
        self,
        customers: pd.DataFrame,
        events: pd.DataFrame,
    ) -> pd.DataFrame:
        """Merge customer data with aggregated event features.
        
        Args:
            customers: Customer DataFrame
            events: Events DataFrame
            
        Returns:
            Enriched customer DataFrame
        """
        if events.empty or customers.empty:
            return customers
        
        # Aggregate events per customer
        event_agg = self._aggregate_events(events)
        
        # Merge with customers
        if "customer_id" in customers.columns and "customer_id" in event_agg.columns:
            merged = customers.merge(
                event_agg, 
                on="customer_id", 
                how="left"
            )
            logger.info(f"Merged customers with event aggregates: {len(merged)} rows")
            return merged
        
        return customers

    def _aggregate_events(self, events: pd.DataFrame) -> pd.DataFrame:
        """Aggregate events by customer with causal feature extraction.
        
        Extracts key causal signals including:
        - Delivery delay metrics (avg, max, late delivery flag)
        - Onboarding completion status
        - Support ticket counts
        - Email engagement rates
        
        Args:
            events: Events DataFrame with columns: customer_id, event_type, 
                    event_properties, event_time
            
        Returns:
            Aggregated features per customer including causal signals
        """
        if "customer_id" not in events.columns:
            return pd.DataFrame()
        
        # Parse delay_days from event_properties (format: "delay_days=5")
        events = events.copy()
        if "event_properties" in events.columns:
            events["delay_days"] = events["event_properties"].apply(
                self._parse_delay_days
            )
        else:
            events["delay_days"] = None
        
        # Basic event aggregation
        agg = events.groupby("customer_id").agg(
            total_events=("event_id", "count"),
            first_event=("event_time", "min"),
            last_event=("event_time", "max"),
        ).reset_index()
        
        # --- Delivery delay features (CAUSAL SIGNAL) ---
        delivery_events = events[events["event_type"] == "delivery"]
        if not delivery_events.empty:
            delivery_agg = delivery_events.groupby("customer_id").agg(
                avg_delivery_delay=("delay_days", "mean"),
                max_delivery_delay=("delay_days", "max"),
                delivery_count=("event_id", "count"),
            ).reset_index()
            # Add boolean flag for late deliveries (delay > 2 days)
            delivery_agg["had_late_delivery"] = delivery_agg["max_delivery_delay"] > 2
            agg = agg.merge(delivery_agg, on="customer_id", how="left")
        
        # --- Onboarding features (CAUSAL SIGNAL) ---
        onboarding_complete = events[events["event_type"] == "complete_onboarding"]
        onboarding_steps = events[events["event_type"] == "view_onboarding_step"]
        
        # Completed onboarding flag
        completed_customers = set(onboarding_complete["customer_id"].unique())
        agg["completed_onboarding"] = agg["customer_id"].isin(completed_customers)
        
        # Onboarding steps viewed count
        if not onboarding_steps.empty:
            steps_agg = onboarding_steps.groupby("customer_id").size().reset_index(
                name="onboarding_steps_viewed"
            )
            agg = agg.merge(steps_agg, on="customer_id", how="left")
        
        # --- Support ticket features (CAUSAL SIGNAL) ---
        # Only count opened tickets (not closed) to avoid double-counting
        support_opened = events[events["event_type"] == "support_ticket_opened"]
        if not support_opened.empty:
            support_agg = support_opened.groupby("customer_id").size().reset_index(
                name="num_support_tickets"
            )
            agg = agg.merge(support_agg, on="customer_id", how="left")
        
        # --- Email engagement features ---
        email_sent = events[events["event_type"] == "email_sent"]
        email_opened = events[events["event_type"] == "email_opened"]
        
        if not email_sent.empty:
            sent_counts = email_sent.groupby("customer_id").size().reset_index(
                name="emails_sent"
            )
            agg = agg.merge(sent_counts, on="customer_id", how="left")
        
        if not email_opened.empty:
            opened_counts = email_opened.groupby("customer_id").size().reset_index(
                name="emails_opened"
            )
            agg = agg.merge(opened_counts, on="customer_id", how="left")
        
        # Calculate email open rate
        if "emails_sent" in agg.columns and "emails_opened" in agg.columns:
            agg["email_open_rate"] = (
                agg["emails_opened"].fillna(0) / agg["emails_sent"].fillna(1)
            ).clip(0, 1)
        
        # --- Session/engagement count ---
        session_events = events[events["event_type"] == "session"]
        if not session_events.empty:
            session_agg = session_events.groupby("customer_id").size().reset_index(
                name="session_count"
            )
            agg = agg.merge(session_agg, on="customer_id", how="left")
        
        # Fill NaN values with appropriate defaults
        numeric_cols = [
            "avg_delivery_delay", "max_delivery_delay", "delivery_count",
            "onboarding_steps_viewed", "num_support_tickets", 
            "emails_sent", "emails_opened", "email_open_rate", "session_count"
        ]
        for col in numeric_cols:
            if col in agg.columns:
                agg[col] = agg[col].fillna(0)
        
        # Fill boolean columns
        if "had_late_delivery" in agg.columns:
            agg["had_late_delivery"] = agg["had_late_delivery"].fillna(False)
        if "completed_onboarding" not in agg.columns:
            agg["completed_onboarding"] = False
        
        logger.info(
            f"Aggregated events for {len(agg)} customers with causal features: "
            f"delivery_delay, onboarding, support_tickets, email_engagement"
        )
        
        return agg

    def _parse_delay_days(self, event_properties: str | None) -> float | None:
        """Parse delay_days value from event_properties string.
        
        Args:
            event_properties: String like "delay_days=5" or None
            
        Returns:
            Parsed delay days as float, or None if not found
        """
        if not event_properties or pd.isna(event_properties):
            return None
        
        try:
            # Handle format: "delay_days=5"
            if "delay_days=" in str(event_properties):
                parts = str(event_properties).split("delay_days=")
                if len(parts) > 1:
                    # Extract numeric value (handle cases like "delay_days=5,other=x")
                    value_str = parts[1].split(",")[0].split(";")[0].strip()
                    return float(value_str)
        except (ValueError, IndexError):
            pass
        
        return None

    def strengthen_causal_signals(
        self, 
        enriched_customers: pd.DataFrame
    ) -> pd.DataFrame:
        """Create explicit causal bins from enriched customer data.
        
        Adds boolean/categorical features that represent causal hypotheses:
        - high_delay_customer: avg_delivery_delay > 3 days
        - incomplete_onboarding: completed_onboarding == False
        - high_support_contact: num_support_tickets > 2
        - low_email_engagement: email_open_rate < 0.2
        
        These features make causal relationships more detectable
        in statistical tests by creating clear treatment/control groups.
        
        Args:
            enriched_customers: Customer DataFrame enriched with event features
            
        Returns:
            DataFrame with additional causal signal features
        """
        df = enriched_customers.copy()
        
        # --- Delivery delay signals ---
        if "avg_delivery_delay" in df.columns:
            df["high_delay_customer"] = df["avg_delivery_delay"] > 3
            df["moderate_delay_customer"] = (
                (df["avg_delivery_delay"] > 1) & (df["avg_delivery_delay"] <= 3)
            )
            logger.debug(
                f"Created delivery delay bins: "
                f"{df['high_delay_customer'].sum()} high delay customers"
            )
        
        # --- Onboarding signals ---
        if "completed_onboarding" in df.columns:
            df["incomplete_onboarding"] = ~df["completed_onboarding"].astype(bool)
            logger.debug(
                f"Created onboarding signal: "
                f"{df['incomplete_onboarding'].sum()} incomplete onboarding"
            )
        
        if "onboarding_steps_viewed" in df.columns:
            df["low_onboarding_engagement"] = df["onboarding_steps_viewed"] < 2
        
        # --- Support contact signals ---
        if "num_support_tickets" in df.columns:
            # Note: Each ticket counts as 1 (we only count opened, not closed)
            df["high_support_contact"] = df["num_support_tickets"] > 1
            df["any_support_contact"] = df["num_support_tickets"] > 0
            logger.debug(
                f"Created support contact bins: "
                f"{df['any_support_contact'].sum()} customers with support contact"
            )
        
        # --- Email engagement signals ---
        if "email_open_rate" in df.columns:
            df["low_email_engagement"] = df["email_open_rate"] < 0.2
            df["high_email_engagement"] = df["email_open_rate"] > 0.5
        
        # --- Session engagement signals ---
        if "session_count" in df.columns:
            df["low_session_engagement"] = df["session_count"] < 3
            df["high_session_engagement"] = df["session_count"] > 10
        
        # --- Combined risk signals ---
        # Create a combined risk score based on multiple causal factors
        risk_factors = []
        if "high_delay_customer" in df.columns:
            risk_factors.append(df["high_delay_customer"].astype(int))
        if "incomplete_onboarding" in df.columns:
            risk_factors.append(df["incomplete_onboarding"].astype(int))
        if "high_support_contact" in df.columns:
            risk_factors.append(df["high_support_contact"].astype(int))
        
        if risk_factors:
            df["causal_risk_score"] = sum(risk_factors)
            df["high_causal_risk"] = df["causal_risk_score"] >= 2
            logger.info(
                f"Created causal risk score: "
                f"{df['high_causal_risk'].sum()} high-risk customers "
                f"({df['high_causal_risk'].mean():.1%} of total)"
            )
        
        return df

    def get_causal_ground_truth(self) -> dict:
        """Return documented causal ground truth for validation.
        
        This documents the designed causal relationships in the synthetic data
        to help validate that the agent is finding real signals.
        
        Returns:
            Dictionary with causal relationships and expected effect sizes
        """
        return {
            "direct_effects": {
                "avg_delivery_delay > 3": {
                    "effect_on": "churn_flag",
                    "expected_direction": "positive",
                    "expected_effect_size": 0.15,  # +15% churn
                    "description": "Late deliveries (>3 days) increase churn"
                },
                "completed_onboarding = False": {
                    "effect_on": "churn_flag", 
                    "expected_direction": "positive",
                    "expected_effect_size": 0.20,  # +20% churn
                    "description": "Incomplete onboarding increases churn"
                },
                "num_support_tickets > 2": {
                    "effect_on": "churn_flag",
                    "expected_direction": "positive", 
                    "expected_effect_size": 0.10,  # +10% churn
                    "description": "High support contact indicates problems"
                },
            },
            "indirect_effects": {
                "late_delivery → low_engagement → churn": {
                    "mediator": "session_count",
                    "description": "Late deliveries reduce engagement, which causes churn"
                },
            },
            "confounders": {
                "brand": {
                    "affects": ["delivery_delay", "churn"],
                    "description": "Some brands have more delays AND higher baseline churn"
                },
            },
        }

    def get_available_features(self, data: dict[str, pd.DataFrame]) -> list[str]:
        """Get list of all available features from loaded data.
        
        Args:
            data: Dictionary of loaded DataFrames
            
        Returns:
            List of feature names
        """
        features = set()
        
        if "customers" in data and not data["customers"].empty:
            features.update(data["customers"].columns.tolist())
        
        return sorted(list(features))

    def get_available_metrics(self, data: dict[str, pd.DataFrame]) -> list[str]:
        """Get list of available metrics from daily metrics data.
        
        Args:
            data: Dictionary of loaded DataFrames
            
        Returns:
            List of metric names
        """
        if "metrics_daily" not in data or data["metrics_daily"].empty:
            return []
        
        if "metric_name" in data["metrics_daily"].columns:
            return data["metrics_daily"]["metric_name"].unique().tolist()
        
        return []

    def get_brands(self, data: dict[str, pd.DataFrame]) -> list[str]:
        """Get list of brands from data.
        
        Args:
            data: Dictionary of loaded DataFrames
            
        Returns:
            List of brand IDs
        """
        brands = set()
        
        for df in data.values():
            if "brand_id" in df.columns:
                brands.update(df["brand_id"].unique().tolist())
        
        return sorted(list(brands))

