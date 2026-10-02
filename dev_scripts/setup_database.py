#!/usr/bin/env python
"""
Database setup script for ByteforgeConverse.

Creates the byteforge_converse database and user, grants permissions, and
applies the canonical schema packaged in byteforge-converse-core.

Environment variables (loaded from .env in the backend repo root):
  BYTEFORGE_CONVERSE_DB_HOST          PostgreSQL host (default: localhost) — same var the app uses
  BYTEFORGE_CONVERSE_DB_PORT          PostgreSQL port (default: 5432)
  BYTEFORGE_CONVERSE_DB_NAME          Application database name (default: byteforge_converse)
  BYTEFORGE_CONVERSE_DB_USER          Application database user (default: byteforge_converse)
  BYTEFORGE_CONVERSE_DB_PASSWORD      Application database user password (REQUIRED)

Usage:
  python dev_scripts/setup_database.py --pg-password <postgres_superuser_password>
  python dev_scripts/setup_database.py --pg-password <pw> --pg-user <superuser>
"""

import os
import sys
import argparse
import logging

from byteforge_converse_core.schema import apply_schema

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import RealDictCursor
from psycopg2 import sql


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    load_dotenv()

    parser = argparse.ArgumentParser(description="Setup ByteforgeConverse database")
    parser.add_argument(
        "--pg-password",
        required=True,
        help="PostgreSQL superuser password (required)",
    )
    parser.add_argument(
        "--pg-user",
        default="postgres",
        help="PostgreSQL superuser name (default: postgres)",
    )
    args = parser.parse_args()

    pg_host = os.environ.get("BYTEFORGE_CONVERSE_DB_HOST", "localhost")
    pg_port = os.environ.get("BYTEFORGE_CONVERSE_DB_PORT", "5432")
    pg_user = args.pg_user
    pg_password = args.pg_password

    app_db = os.environ.get("BYTEFORGE_CONVERSE_DB_NAME", "byteforge_converse")
    app_user = os.environ.get("BYTEFORGE_CONVERSE_DB_USER", "byteforge_converse")
    app_password = os.environ.get("BYTEFORGE_CONVERSE_DB_PASSWORD")

    if app_password is None:
        logging.error(
            "Error: BYTEFORGE_CONVERSE_DB_PASSWORD environment variable is required"
        )
        sys.exit(1)

    logging.info(f"Setting up database '{app_db}' and user '{app_user}'...")
    logging.info(f"Connecting to PostgreSQL at {pg_host}:{pg_port} as {pg_user}")

    try:
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database="postgres",
            user=pg_user,
            password=pg_password,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (app_user,))
            if not cursor.fetchone():
                logging.info(f"Creating user '{app_user}'...")
                cursor.execute(
                    sql.SQL("CREATE USER {} WITH PASSWORD %s").format(
                        sql.Identifier(app_user)
                    ),
                    (app_password,),
                )
                logging.info(f"✓ User '{app_user}' created")
            else:
                logging.info(f"✓ User '{app_user}' already exists")

            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (app_db,))
            if not cursor.fetchone():
                logging.info(f"Creating database '{app_db}'...")
                cursor.execute(
                    sql.SQL(
                        "CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0"
                    ).format(sql.Identifier(app_db), sql.Identifier(app_user))
                )
                logging.info(f"✓ Database '{app_db}' created")
            else:
                logging.info(f"✓ Database '{app_db}' already exists")

            logging.info("Setting permissions...")
            cursor.execute(
                sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                    sql.Identifier(app_db), sql.Identifier(app_user)
                )
            )
            logging.info(f"✓ Granted all privileges on '{app_db}' to '{app_user}'")

        conn.close()

        logging.info(f"\nConnecting as '{app_user}' to apply schema...")
        app_conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database=app_db,
            user=app_user,
            password=app_password,
        )
        app_conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        with app_conn:
            logging.info("Applying packaged Converse schema...")
            apply_schema(app_conn)

        app_conn.close()
        logging.info("✓ Database setup complete")
        logging.info(f"  Database: {app_db}")
        logging.info(f"  User:     {app_user}")
        logging.info(f"  Host:     {pg_host}:{pg_port}")

    except psycopg2.Error as e:
        logging.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
