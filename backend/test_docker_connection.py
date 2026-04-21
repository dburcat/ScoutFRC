"""
Test Docker PostgreSQL connection for ScouterFRC.

Usage:
    python test_docker_connection.py

Reads connection settings from .env file (or environment variables).
"""

import os
import sys

try:
    from dotenv import load_dotenv
except ImportError:
    print("✗ python-dotenv is not installed. Run: pip install python-dotenv")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("✗ psycopg2 is not installed. Run: pip install psycopg2-binary")
    sys.exit(1)


def test_connection() -> None:
    # Load environment variables from .env file if present
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "scouterfrc")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "password")

    print("ScouterFRC — PostgreSQL Connection Test")
    print("=" * 40)

    if database_url:
        print(f"  Using DATABASE_URL from environment")
        conn_kwargs = {"dsn": database_url}
    else:
        print(f"  Host:     {db_host}")
        print(f"  Port:     {db_port}")
        print(f"  Database: {db_name}")
        print(f"  User:     {db_user}")
        conn_kwargs = {
            "host": db_host,
            "port": int(db_port),
            "dbname": db_name,
            "user": db_user,
            "password": db_password,
        }

    print("")

    try:
        conn = psycopg2.connect(**conn_kwargs)
        cursor = conn.cursor()

        # Query PostgreSQL version
        cursor.execute("SELECT version();")
        version_row = cursor.fetchone()
        version = version_row[0] if version_row else "unknown"

        # Query current database and user
        cursor.execute("SELECT current_database(), current_user;")
        db_row = cursor.fetchone()
        current_db, current_user = (db_row[0], db_row[1]) if db_row else ("?", "?")

        # Count visible tables
        cursor.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';"
        )
        table_row = cursor.fetchone()
        table_count = table_row[0] if table_row else 0

        cursor.close()
        conn.close()

        print("✅ Connected to PostgreSQL successfully!")
        print(f"   Server version: {version}")
        print(f"   Database:       {current_db}")
        print(f"   User:           {current_user}")
        print(f"   Tables in public schema: {table_count}")

    except psycopg2.OperationalError as exc:
        print(f"✗ Connection failed: {exc}")
        print("")
        print("Troubleshooting tips:")
        print("  1. Is the Docker container running?  →  docker ps")
        print("  2. Start it with:                   →  docker start scouterfrc-db")
        print("  3. Or use the helper:               →  ./docker-helpers.sh start")
        sys.exit(1)


if __name__ == "__main__":
    test_connection()
