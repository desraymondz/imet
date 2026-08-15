"""
Create imet_eval (if not exists), apply the app contact schema, then load
eval/datasets/recall/contacts.jsonl with stable ids and BGE embeddings.

Pipeline:
    1. CREATE DATABASE imet_eval if it does not exist
    2. CREATE EXTENSION vector and users/contacts tables (same models as the app)
    3. Populate contacts table
    4. Embed each profile_text

Usage
    python eval/scripts/recall/seed_eval_db.py

Requires
    Postgres on EVAL_DATABASE_URL (same server as imet_db, database imet_eval)
    EVAL_DATABASE_URL in .env.local
    EMBEDDING_MODEL (BAAI/bge-base-en-v1.5)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]
CONTACTS_PATH = REPO_ROOT / "eval" / "datasets" / "recall" / "contacts.jsonl"

# Dummy owner required by contacts.owner_id (not used in eval scoring)
EVAL_USER_EMAIL = "eval@imet.local"
EVAL_OWNER_ID = 1

CONTACT_FIELDS = (
    "display_name",
    "email",
    "phone",
    "company",
    "role",
    "location",
    "profile_text",
    "keywords",
)


def load_env() -> None:
    """
    Load environment variables from then add the repo root to sys.path.
    """
    # Load environment variables
    load_dotenv(REPO_ROOT / ".env.local")
    # Puts repo root on Python import path to import backend models
    sys.path.insert(0, str(REPO_ROOT))


def eval_database_url() -> URL:
    """
    Return EVAL_DATABASE_URL from the environment.
    """
    raw = os.environ.get("EVAL_DATABASE_URL", "").strip()
    if not raw:
        raise SystemExit(
            "EVAL_DATABASE_URL is missing. Set it in .env.local "
        )
    return make_url(raw)


def ensure_eval_database(eval_db_url: URL) -> None:
    """
    Make sure the eval database exists on the same server as the app database.
    Docker compose does not create the eval database, so we need to do it manually.

    Steps:
    1. Connect through the app database
    2. Create EVAL_DATABASE_URL's database if does not exist
    """
    # Step 1: Connect through the app database
    app_db_name = os.environ.get("POSTGRES_DB", "imet_db").strip() or "imet_db"
    app_db_url = eval_db_url.set(database=app_db_name)
    engine = create_engine(app_db_url, isolation_level="AUTOCOMMIT")
    eval_db_name = eval_db_url.database
    if not eval_db_name:
        raise SystemExit("EVAL_DATABASE_URL must include a database name")

    # Step 2: Create the eval database if it does not exist
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": eval_db_name},
        ).scalar()
        if exists:
            print(f"Database {eval_db_name} already exists")
            engine.dispose()
            return
        conn.execute(text(f'CREATE DATABASE "{eval_db_name}"'))
        print(f"Created database {eval_db_name}")

    engine.dispose()


def init_schema(eval_engine) -> None:
    """
    Enable pgvector then create users and contacts tables.
    """
    from backend.db import Base
    # Register tables for SQLAlchemy
    from backend.models import Contact, User

    # Step 1: Enable the pgvector extension
    with eval_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    # Step 2: Create all tables (users and contacts)
    Base.metadata.create_all(bind=eval_engine)
    print("Schema ready (vector extension, users, contacts)")


def load_contact_rows(path: Path) -> list[dict]:
    """
    Load contact seed rows from a JSONL file then convert into a list of dictionaries
    """
    rows: list[dict] = []

    # Read the JSONL file line by line
    for line in path.read_text(encoding="utf-8").splitlines():
        # Skip empty lines
        if not line.strip():
            continue
        # Parse JSON and add to list
        rows.append(json.loads(line))

    if not rows:
        raise SystemExit(f"No contacts in {path}")
    return rows


def ensure_eval_user(session) -> None:
    """
    Insert the dummy eval owner user if it does not exist.
    """
    from backend.models import User

    # Skip if the dummy owner already exists
    user = session.get(User, EVAL_OWNER_ID)
    if user is not None:
        return

    # Insert a placeholder user so contacts can satisfy the owner FK
    session.add(
        User(
            id=EVAL_OWNER_ID,
            email=EVAL_USER_EMAIL,
            hashed_password="eval-unused",
        )
    )
    session.flush()
    print(f"Created eval user id={EVAL_OWNER_ID}")


def seed_contacts(session, rows: list[dict]) -> None:
    """
    Delete existing eval contacts then insert seed rows and embed profile_text.

    Steps:
    1. Delete existing eval contacts
    2. Load the embedding model
    3. Insert each JSONL row with a explicit id and profile_embedding
    """
    from backend.ai.embeddings.bge import get_embedder
    from backend.models import Contact

    # Step 1: Delete existing eval contacts
    session.query(Contact).filter(Contact.owner_id == EVAL_OWNER_ID).delete()
    session.flush()

    # Step 2: Load the embedding model
    embedder = get_embedder()
    print(f"Embedding {len(rows)} profile_text values...")

    # Step 3: Insert each JSONL row with a explicit id and profile_embedding
    for row in rows:
        contact_id = int(row["id"])
        profile_text = (row.get("profile_text") or "").strip()

        # Copy structured fields from the JSONL row
        fields = {name: row.get(name) for name in CONTACT_FIELDS}
        session.add(
            Contact(
                id=contact_id,
                owner_id=EVAL_OWNER_ID,
                profile_embedding=embedder.embed_text(profile_text),
                **fields,
            )
        )

    session.commit()
    print(f"Inserted {len(rows)} contacts")


def main() -> None:
    """
    Main recall eval database seed pipeline.

    Steps:
    1. Load environment variables
    2. Create imet_eval if it does not exist
    3. Open an eval-db session then create schema and dummy owner
    4. Load JSONL rows and populate contacts
    """
    # Step 1: Load environment variables
    load_env()
    eval_db_url = eval_database_url()

    if not CONTACTS_PATH.is_file():
        raise SystemExit(f"Missing seed file: {CONTACTS_PATH}")

    # Step 2: Create imet_eval if it does not exist
    ensure_eval_database(eval_db_url)

    # Step 3: Open an eval-db session then create schema and dummy owner
    eval_engine = create_engine(eval_db_url, pool_pre_ping=True)
    init_schema(eval_engine)
    SessionLocal = sessionmaker(bind=eval_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        ensure_eval_user(session)
        # Step 4: Load JSONL rows and populate contacts
        rows = load_contact_rows(CONTACTS_PATH)
        seed_contacts(session, rows)
    finally:
        session.close()
        eval_engine.dispose()


if __name__ == "__main__":
    main()