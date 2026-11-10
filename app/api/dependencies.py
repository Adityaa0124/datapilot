"""
FastAPI Dependencies Module

Assembles database sessions, repositories, and query service for API endpoints.
Provides graceful fallback to standalone mode when external Docker infrastructure
(MySQL, Qdrant, Elasticsearch, Embedding service) is not running.
"""

import os
from typing import Annotated, Any, Optional
from fastapi import Depends

try:
    from langchain_huggingface import HuggingFaceEndpointEmbeddings
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.clients.embedding_client_manager import embedding_client_manager
    from app.clients.es_client_manager import es_client_manager
    from app.clients.mysql_client_manager import (
        dw_mysql_client_manager,
        meta_mysql_client_manager,
    )
    from app.clients.qdrant_client_manager import qdrant_client_manager
    from app.repositories.es.value_es_repository import ValueESRepository
    from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
    from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
    from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
    from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
    from app.services.query_service import QueryService
    _DRIVERS_AVAILABLE = True
except ImportError:
    _DRIVERS_AVAILABLE = False


def is_external_enabled() -> bool:
    return os.getenv("ENABLE_EXTERNAL_SERVICES", "false").lower() in ("true", "1")


async def get_meta_session():
    """Yields metadata database session if external services are enabled"""
    if not _DRIVERS_AVAILABLE or not is_external_enabled():
        yield None
        return
    try:
        async with meta_mysql_client_manager.session_factory() as meta_session:
            yield meta_session
    except Exception:
        yield None


async def get_meta_mysql_repository(
    session: Annotated[Optional[Any], Depends(get_meta_session)] = None,
) -> Optional[Any]:
    if session is None or not _DRIVERS_AVAILABLE or not is_external_enabled():
        return None
    try:
        return MetaMySQLRepository(session)
    except Exception:
        return None


async def get_embedding_client() -> Optional[Any]:
    if not _DRIVERS_AVAILABLE or not is_external_enabled():
        return None
    try:
        return embedding_client_manager.client
    except Exception:
        return None


async def get_dw_session():
    """Yields data warehouse database session if external services are enabled"""
    if not _DRIVERS_AVAILABLE or not is_external_enabled():
        yield None
        return
    try:
        async with dw_mysql_client_manager.session_factory() as dw_session:
            yield dw_session
    except Exception:
        yield None


async def get_dw_mysql_repository(
    session: Annotated[Optional[Any], Depends(get_dw_session)] = None,
) -> Optional[Any]:
    if session is None or not _DRIVERS_AVAILABLE or not is_external_enabled():
        return None
    try:
        return DWMySQLRepository(session)
    except Exception:
        return None


async def get_column_qdrant_repository() -> Optional[Any]:
    if not _DRIVERS_AVAILABLE or not is_external_enabled():
        return None
    try:
        return ColumnQdrantRepository(qdrant_client_manager.client)
    except Exception:
        return None


async def get_metric_qdrant_repository() -> Optional[Any]:
    if not _DRIVERS_AVAILABLE or not is_external_enabled():
        return None
    try:
        return MetricQdrantRepository(qdrant_client_manager.client)
    except Exception:
        return None


async def get_value_es_repository() -> Optional[Any]:
    if not _DRIVERS_AVAILABLE or not is_external_enabled():
        return None
    try:
        return ValueESRepository(es_client_manager.client)
    except Exception:
        return None


async def get_query_service(
    meta_mysql_repository: Annotated[Optional[Any], Depends(get_meta_mysql_repository)] = None,
    embedding_client: Annotated[Optional[Any], Depends(get_embedding_client)] = None,
    dw_mysql_repository: Annotated[Optional[Any], Depends(get_dw_mysql_repository)] = None,
    column_qdrant_repository: Annotated[Optional[Any], Depends(get_column_qdrant_repository)] = None,
    metric_qdrant_repository: Annotated[Optional[Any], Depends(get_metric_qdrant_repository)] = None,
    value_es_repository: Annotated[Optional[Any], Depends(get_value_es_repository)] = None,
) -> Optional[Any]:
    if not _DRIVERS_AVAILABLE or not is_external_enabled() or any(
        dep is None
        for dep in [
            meta_mysql_repository,
            embedding_client,
            dw_mysql_repository,
            column_qdrant_repository,
            metric_qdrant_repository,
            value_es_repository,
        ]
    ):
        return None

    try:
        return QueryService(
            meta_mysql_repository=meta_mysql_repository,
            embedding_client=embedding_client,
            dw_mysql_repository=dw_mysql_repository,
            column_qdrant_repository=column_qdrant_repository,
            metric_qdrant_repository=metric_qdrant_repository,
            value_es_repository=value_es_repository,
        )
    except Exception:
        return None
