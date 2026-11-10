"""
FastAPI 应用生命周期管理
Handles startup and shutdown of external database and search clients.
Includes resilient fallback to standalone development database mode when
external Docker services are not running.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.log import logger

try:
    from app.clients.embedding_client_manager import embedding_client_manager
    from app.clients.es_client_manager import es_client_manager
    from app.clients.mysql_client_manager import (
        dw_mysql_client_manager,
        meta_mysql_client_manager,
    )
    from app.clients.qdrant_client_manager import qdrant_client_manager
    _CLIENTS_AVAILABLE = True
except ImportError as e:
    _CLIENTS_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理应用启动和关闭两个阶段的外部资源"""
    enable_external = os.getenv("ENABLE_EXTERNAL_SERVICES", "false").lower() in ("true", "1")
    external_services_available = False

    if _CLIENTS_AVAILABLE and enable_external:
        try:
            qdrant_client_manager.init()
            embedding_client_manager.init()
            es_client_manager.init()
            meta_mysql_client_manager.init()
            dw_mysql_client_manager.init()
            external_services_available = True
            logger.info("External services (MySQL, Qdrant, ES, Embeddings) initialized successfully.")
        except Exception as e:
            logger.warning(
                f"External infrastructure unavailable ({e}). "
                "DataPilot running in standalone Synthetic Development Database mode."
            )
    else:
        logger.info("DataPilot operating in zero-dependency Synthetic Development Database mode.")

    yield

    # Shutdown
    if external_services_available and _CLIENTS_AVAILABLE:
        try:
            await qdrant_client_manager.close()
        except Exception:
            pass
        try:
            await es_client_manager.close()
        except Exception:
            pass
        try:
            await meta_mysql_client_manager.close()
        except Exception:
            pass
        try:
            await dw_mysql_client_manager.close()
        except Exception:
            pass
