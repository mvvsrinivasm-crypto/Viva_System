"""
Secure Neon PostgreSQL Connection & Schema Verifier
===================================================
Tests active connection to Neon PostgreSQL without displaying credentials.
Verifies engine type, database tables, and schema integrity.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def verify_connection():
    db_url = os.getenv("DATABASE_URL", "").strip()
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    if not db_url or not db_url.startswith("postgresql://"):
        print("[ERROR] DATABASE_URL is missing or does not start with postgresql:// in backend/.env.")
        print("Please configure your real Neon connection string in backend/.env.")
        return False

    # Extract host and database name safely without exposing credentials
    try:
        from urllib.parse import urlparse
        parsed = urlparse(db_url)
        safe_host = parsed.hostname or "unknown-host"
        safe_db = parsed.path.lstrip("/") or "unknown-db"
        print(f"Connecting to Neon PostgreSQL at host '{safe_host}', database '{safe_db}'...")
    except Exception:
        print("Connecting to Neon PostgreSQL...")

    try:
        engine = create_engine(db_url, pool_pre_ping=True)
        with engine.connect() as conn:
            res = conn.execute(text("SELECT version();")).fetchone()
            print("  -> Connection Successful!")
            print(f"  -> PostgreSQL Server Version: {res[0][:50]}...")

            # Check schema tables
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            print(f"  -> Tables found in database ({len(existing_tables)}): {', '.join(sorted(existing_tables)) if existing_tables else 'None'}")

            expected_tables = ["users", "vivas", "documents", "questions", "viva_sessions", "session_questions", "answers", "evaluations", "results"]
            missing = [t for t in expected_tables if t not in existing_tables]
            if missing:
                print(f"  -> Missing tables: {missing} (Can be created via db.create_all() or migration script)")
            else:
                print("  -> All core required tables are present in schema!")

        print("\n=======================================================")
        print("VERIFICATION SUCCESS: Active database engine is PostgreSQL!")
        print("=======================================================")
        return True
    except Exception as e:
        print(f"[ERROR] Could not connect to Neon PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    ok = verify_connection()
    sys.exit(0 if ok else 1)
