"""
Application Configuration Module

Defines structured configuration models mapping to `conf/app_config.yaml`.
Loads environment variables and YAML settings using OmegaConf to provide typed access
to logging, MySQL, Qdrant, Embedding, Elasticsearch, and LLM parameters.
"""

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from omegaconf import OmegaConf


@dataclass
class File:
    """File logging configuration."""
    enable: bool
    level: str
    path: str
    rotation: str
    retention: str


@dataclass
class Console:
    """Console logging configuration."""
    enable: bool
    level: str


@dataclass
class LoggingConfig:
    """Aggregate logging configuration."""
    file: File
    console: Console


@dataclass
class DBConfig:
    """MySQL database connection configuration."""
    host: str
    port: int
    user: str
    password: str
    database: str


@dataclass
class QdrantConfig:
    """Qdrant vector store connection and embedding dimensions."""
    host: str
    port: int
    embedding_size: int


@dataclass
class EmbeddingConfig:
    """Text embedding inference service configuration."""
    host: str
    port: int
    model: str


@dataclass
class ESConfig:
    """Elasticsearch search engine configuration."""
    host: str
    port: int
    index_name: str


@dataclass
class LLMConfig:
    """Large Language Model API configuration."""
    model_name: str
    api_key: str
    base_url: str


@dataclass
class AppConfig:
    """Root configuration schema for DataPilot."""
    logging: LoggingConfig
    db_meta: DBConfig
    db_dw: DBConfig
    qdrant: QdrantConfig
    embedding: EmbeddingConfig
    es: ESConfig
    llm: LLMConfig


# Locate project root and configuration YAML
project_root = Path(__file__).parents[2]
config_file = project_root / "conf" / "app_config.yaml"

# Load local environment variables for sensitive parameters
load_dotenv(project_root / ".env")

# Load YAML configuration with fallback
if config_file.exists():
    context = OmegaConf.load(config_file)
    schema = OmegaConf.structured(AppConfig)
    app_config: AppConfig = OmegaConf.to_object(OmegaConf.merge(schema, context))
else:
    schema = OmegaConf.structured(AppConfig)
    app_config: AppConfig = OmegaConf.to_object(schema)

if __name__ == "__main__":
    print(f"ES Host: {app_config.es.host}")
