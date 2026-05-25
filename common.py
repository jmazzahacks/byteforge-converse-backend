"""
Singleton manager for shared service instances.

Provides centralized initialization of database connections, LLM clients,
and other shared resources used across blueprints.
"""

import uuid
import logging
from typing import Optional

from flask import Request
from flask_smorest import abort
from byteforge_converse_core import Database, DatabaseConfig, ChatService, LLMConfig


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


def require_uuid(value: str, label: str = "Resource") -> None:
    """
    Abort 404 when a path id is not a well-formed UUID.

    Keeps malformed ids out of the DB layer, where they would otherwise raise a
    psycopg2 DataError and surface as a 500 instead of a clean not-found.
    """
    try:
        uuid.UUID(value)
    except ValueError:
        abort(404, message=f"{label} not found: {value}")


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
        self._chat_service: Optional[ChatService] = None
        self._initialized = True
        logger.info("ServiceManager initialized")

    def get_database(self) -> Database:
        """
        Get the database instance (lazy initialization).

        The connection pool is created on first use so it is built inside the
        gunicorn worker (post-fork), not in the master process at import time.

        Note: the lazy init below is not lock-guarded. That is safe under the
        default sync gunicorn workers (single-threaded). If you switch to
        threaded/gevent workers, guard these with a lock to avoid two threads
        each building a pool.
        """
        if self._db is None:
            self._db = Database(DatabaseConfig.from_env())
        return self._db

    def get_chat_service(self) -> ChatService:
        """
        Get the chat orchestration service (lazy initialization).

        Built on first use so the OpenRouter client and DB pool are created
        inside the gunicorn worker, not the master process.
        """
        if self._chat_service is None:
            self._chat_service = ChatService(self.get_database(), LLMConfig.from_env())
        return self._chat_service


service_manager = ServiceManager()
