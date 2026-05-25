#!/usr/bin/env python
"""
Database setup script for ByteforgeConverse.

Creates the byteforge_converse database and user, grants permissions, and
applies database/schema.sql.

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

import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


def main() -> None:
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
        print("Error: BYTEFORGE_CONVERSE_DB_PASSWORD environment variable is required")
        sys.exit(1)

    print(f"Setting up database '{app_db}' and user '{app_user}'...")
    print(f"Connecting to PostgreSQL at {pg_host}:{pg_port} as {pg_user}")

    try:
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database="postgres",
            user=pg_user,
            password=pg_password,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (app_user,))
            if not cursor.fetchone():
                print(f"Creating user '{app_user}'...")
                cursor.execute(f'CREATE USER "{app_user}" WITH PASSWORD %s', (app_password,))
                print(f"✓ User '{app_user}' created")
            else:
                print(f"✓ User '{app_user}' already exists")

            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (app_db,))
            if not cursor.fetchone():
                print(f"Creating database '{app_db}'...")
                cursor.execute(f'CREATE DATABASE "{app_db}" OWNER "{app_user}"')
                print(f"✓ Database '{app_db}' created")
            else:
                print(f"✓ Database '{app_db}' already exists")

            print("Setting permissions...")
            cursor.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{app_db}" TO "{app_user}"')
            print(f"✓ Granted all privileges on '{app_db}' to '{app_user}'")

        conn.close()

        print(f"\nConnecting as '{app_user}' to apply schema...")
        app_conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            database=app_db,
            user=app_user,
            password=app_password,
        )
        app_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        schema_path = os.path.join(repo_root, "database", "schema.sql")
        if not os.path.exists(schema_path):
            print(f"Error: schema file not found at {schema_path}")
            sys.exit(1)

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with app_conn.cursor() as cursor:
            print("Ensuring required extensions...")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
            print(f"Applying schema from {schema_path}...")
            cursor.execute(schema_sql)
            print("✓ Schema applied")

        app_conn.close()
        print("✓ Database setup complete")
        print(f"  Database: {app_db}")
        print(f"  User:     {app_user}")
        print(f"  Host:     {pg_host}:{pg_port}")

    except psycopg2.Error as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
