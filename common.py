"""
Singleton manager for shared service instances.

Provides centralized initialization of database connections, LLM clients,
and other shared resources used across blueprints.
"""

import os
import logging
from typing import Optional


logger = logging.getLogger(__name__)


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

        self._db = None
        self._initialized = True
        logger.info("ServiceManager initialized")

    def get_database(self):
        """
        Get database connection instance (lazy initialization).
        """
        if self._db is None:
            # TODO: replace with the real Database class once postgres-setup
            # has been run and a database module exists.
            db_host = os.environ.get("BYTEFORGE_CONVERSE_DB_HOST", "localhost")
            db_name = os.environ.get("BYTEFORGE_CONVERSE_DB_NAME", "byteforge_converse")
            db_user = os.environ.get("BYTEFORGE_CONVERSE_DB_USER", "byteforge_converse")
            db_passwd = os.environ.get("BYTEFORGE_CONVERSE_DB_PASSWORD")

            if not db_passwd:
                raise ValueError(
                    "BYTEFORGE_CONVERSE_DB_PASSWORD environment variable required"
                )

            raise NotImplementedError(
                "Database class not yet wired — run the postgres-setup skill "
                "and import the resulting Database here."
            )

        return self._db


service_manager = ServiceManager()
