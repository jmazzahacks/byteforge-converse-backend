"""
Singleton manager for shared service instances.

Provides centralized initialization of database connections, LLM clients,
and other shared resources used across blueprints.
"""

import logging
from typing import Optional

from flask import Request
from byteforge_converse_core import Database, DatabaseConfig


logger = logging.getLogger(__name__)


def get_user_id(req: Request) -> Optional[str]:
    """
    Resolve the calling user's id.

    Auth is delegated upstream: prefer the gateway-injected `X-User-Id`
    header. As a development fallback (no gateway in front), accept a
    `user_id` in the JSON body or query string.
    """
    header_user_id = req.headers.get("X-User-Id")
    if header_user_id:
        return header_user_id

    body = req.get_json(silent=True) or {}
    return body.get("user_id") or req.args.get("user_id")


class ServiceManager:
    """
    Singleton manager for shared service instances.

    Ensures only one instance of each service is created and reused
    across all blueprints.
    """

    _instance: Optional["ServiceManager"] = None

    def __new__(cls) -> "ServiceManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._db: Optional[Database] = None
        self._initialized = True
        logger.info("ServiceManager initialized")

    def get_database(self) -> Database:
        """
        Get the database instance (lazy initialization).

        The connection pool is created on first use so it is built inside the
        gunicorn worker (post-fork), not in the master process at import time.
        """
        if self._db is None:
            self._db = Database(DatabaseConfig.from_env())
        return self._db


service_manager = ServiceManager()
