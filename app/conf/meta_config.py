"""
Metadata Knowledge Catalog Configuration

Defines dataclasses for parsing `conf/meta_config.yaml`.
Describes tables, columns, sample values, business roles, and metrics
for metadata synchronization and schema-aware retrieval.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ColumnConfig:
    """Column configuration defining role, description, aliases, and value sync flags."""
    name: str
    role: str
    description: str
    alias: list[str]
    sync: bool


@dataclass
class TableConfig:
    """Table configuration defining table role, business description, and associated columns."""
    name: str
    role: str
    description: str
    columns: list[ColumnConfig]


@dataclass
class MetricConfig:
    """Metric configuration mapping analytical KPIs to underlying table columns."""
    name: str
    description: str
    relevant_columns: list[str]
    alias: list[str]


@dataclass
class MetaConfig:
    """Root configuration for metadata synchronization."""
    tables: Optional[list[TableConfig]] = None
    metrics: Optional[list[MetricConfig]] = None
