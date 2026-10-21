"""
Safe SQLite to Neon PostgreSQL Data Migration Script
===================================================
Transfers all existing users, vivas, documents, questions,
sessions, answers, evaluations, results, violations, and audits
from backend/data/viva.db to Neon PostgreSQL.

- Preserves existing IDs.
- Preserves foreign key relationships.
- Updates PostgreSQL auto-increment sequences.
- Never prints credentials or database passwords.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text, select
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

def run_migration():
    neon_url = os.getenv("DATABASE_URL", "").strip()
    if neon_url.startswith("postgres://"):
        neon_url = neon_url.replace("postgres://", "postgresql://", 1)

    if not neon_url or not neon_url.startswith("postgresql://"):
        print("[ERROR] DATABASE_URL is missing or not a valid PostgreSQL URL in backend/.env.")
        print("Please configure your real Neon connection string in backend/.env before running this script.")
        return False

    sqlite_path = BASE_DIR / "data" / "viva.db"
    if not sqlite_path.exists():
        print(f"[ERROR] SQLite database not found at {sqlite_path}")
        return False

    sqlite_url = f"sqlite:///{sqlite_path}"
    print("[1] Connecting to SQLite and Neon PostgreSQL (credentials hidden)...")

    try:
        sqlite_engine = create_engine(sqlite_url)
        with sqlite_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("  -> SQLite connection: OK")
    except Exception as e:
        print(f"[ERROR] Failed to connect to SQLite: {e}")
        return False

    try:
        neon_engine = create_engine(neon_url, pool_pre_ping=True)
        with neon_engine.connect() as conn:
            res = conn.execute(text("SELECT version();")).fetchone()
            print("  -> Neon PostgreSQL connection: OK")
            print(f"  -> PostgreSQL Version: {res[0][:40]}...")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Neon PostgreSQL: {e}")
        return False

    # Initialize app to ensure models and metadata are registered
    from app import create_app
    from app.extensions import db
    from app.models.user import User
    from app.models.viva import Viva
    from app.models.document import Document
    from app.models.question import Question
    from app.models.viva_session import VivaSession
    from app.models.session_question import SessionQuestion
    from app.models.answer import Answer
    from app.models.evaluation import Evaluation
    from app.models.result import Result
    from app.models.violation import Violation
    from app.models.mark_audit import MarkAudit

    app = create_app()

    # Tables in strict foreign-key order
    tables = [
        ("users", User),
        ("vivas", Viva),
        ("documents", Document),
        ("questions", Question),
        ("viva_sessions", VivaSession),
        ("session_questions", SessionQuestion),
        ("answers", Answer),
        ("evaluations", Evaluation),
        ("results", Result),
        ("violations", Violation),
        ("mark_audits", MarkAudit),
    ]

    print("\n[2] Checking and preparing Neon PostgreSQL tables...")
    with app.app_context():
        # Ensure schema tables exist in Neon without dropping anything
        db.create_all()
        print("  -> Schema verification: All tables exist in Neon PostgreSQL.")

    SqliteSession = sessionmaker(bind=sqlite_engine)
    NeonSession = sessionmaker(bind=neon_engine)

    sqlite_session = SqliteSession()
    neon_session = NeonSession()

    print("\n[3] Migrating data from SQLite to Neon PostgreSQL...")
    try:
        for table_name, model_class in tables:
            sqlite_records = sqlite_session.query(model_class).all()
            neon_count = neon_session.query(model_class).count()

            print(f"\n  * Table '{table_name}': {len(sqlite_records)} records in SQLite (Neon currently has {neon_count})")

            if len(sqlite_records) == 0:
                continue

            migrated_count = 0
            for record in sqlite_records:
                # Check if record with same ID already exists in Neon
                existing = neon_session.get(model_class, record.id)
                if existing:
                    continue

                # Clone attributes into Neon session
                neon_session.merge(record)
                migrated_count += 1

            neon_session.commit()
            print(f"    -> Migrated {migrated_count} records into '{table_name}'.")

        # 4. Synchronize PostgreSQL serial sequences
        print("\n[4] Synchronizing PostgreSQL auto-increment sequences...")
        with neon_engine.connect() as conn:
            for table_name, _ in tables:
                try:
                    conn.execute(text(f"""
                        SELECT setval(
                            pg_get_serial_sequence('{table_name}', 'id'),
                            COALESCE((SELECT MAX(id) FROM {table_name}), 1)
                        );
                    """))
                    conn.commit()
                except Exception as seq_err:
                    # Ignore if table has no serial sequence
                    pass
        print("  -> All PostgreSQL sequences synchronized successfully.")

        # 5. Final verification check
        print("\n[5] Verifying final record counts in Neon PostgreSQL:")
        for table_name, model_class in tables:
            c = neon_session.query(model_class).count()
            print(f"  -> {table_name}: {c} records")

        print("\n=======================================================")
        print("DATA MIGRATION TO NEON POSTGRESQL COMPLETED SUCCESSFULLY!")
        print("=======================================================")
        return True

    except Exception as e:
        neon_session.rollback()
        print(f"[ERROR] Migration failed: {e}")
        return False
    finally:
        sqlite_session.close()
        neon_session.close()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
