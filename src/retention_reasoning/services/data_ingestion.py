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
        """Aggregate events by customer.
        
        Args:
            events: Events DataFrame
            
        Returns:
            Aggregated features per customer
        """
        if "customer_id" not in events.columns:
            return pd.DataFrame()
        
        agg = events.groupby("customer_id").agg(
            total_events=("event_id", "count"),
            event_types=("event_type", lambda x: list(x.unique())),
            first_event=("event_time", "min"),
            last_event=("event_time", "max"),
        ).reset_index()
        
        # Count specific event types
        if "event_type" in events.columns:
            event_counts = events.groupby(
                ["customer_id", "event_type"]
            ).size().unstack(fill_value=0)
            event_counts.columns = [f"count_{col}" for col in event_counts.columns]
            agg = agg.merge(event_counts.reset_index(), on="customer_id", how="left")
        
        return agg

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

