# Shared pytest setup
import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent
_env = dotenv_values(ROOT / ".env.local")

# Same Postgres server as dev, but a separate database called imet_test
# A shell variable wins over .env.local (e.g. for CI)
raw_url = os.getenv("TEST_DATABASE_URL") or _env.get("TEST_DATABASE_URL")
if not raw_url:
    raise RuntimeError("Set TEST_DATABASE_URL in .env.local (see .env.example)")
test_url = make_url(raw_url)

# Safety guard: refuse to run against any database not named *_test
if not (test_url.database or "").endswith("_test"):
    raise RuntimeError(f"Refusing to run tests against database '{test_url.database}'")

# Environment variables take priority over .env.local in pydantic-settings
os.environ["DATABASE_URL"] = test_url.render_as_string(hide_password=False)
# TestClient talks plain http, and a Secure cookie would never be sent back over it
os.environ["COOKIE_SECURE"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from unittest.mock import create_autospec

from tests.mock_embedder import topic_vector


@pytest.fixture(scope="session")
def database():
    """Create imet_test if missing, then give every session a freshly built schema."""
    # CREATE DATABASE cannot run inside a transaction, so connect to the dev database
    admin_engine = create_engine(_env["DATABASE_URL"], isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": test_url.database},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    admin_engine.dispose()

    from backend.db import Base, engine, init_db

    # Create the vector extension and tables, then rebuild them so the schema matches the models
    init_db()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db(database):
    """Empty the tables after each test, so every test starts from a clean database."""
    yield database
    with database.begin() as conn:
        conn.execute(text("TRUNCATE users, contacts RESTART IDENTITY CASCADE"))


@pytest.fixture
def db_session(db):
    """A session for checking rows directly, used to check whether an embedding was stored."""
    from backend.db import SessionLocal

    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def llm(monkeypatch):
    """
    Mock LLM

    Tests script each recall phase by setting return values:
        llm.understand_recall_query.return_value = None   # understanding failed
        llm.filter_recall_matches.return_value = [3, 1]   # ids the filter keeps
    """
    from backend.ai.llm.ollama import OllamaLLM
    from backend.schemas import ContactExtract, RecallQueryPlan

    # A mock with OllamaLLM's methods
    # A call that does not match the real class fails
    mock = create_autospec(OllamaLLM, instance=True)
    # Default plan when the query is in scope and searches for "hiking"
    mock.understand_recall_query.return_value = RecallQueryPlan(in_scope=True, keywords=["hiking"])

    # Default when the filter fails
    # Routes fall back to the merged retrieval results
    mock.filter_recall_matches.return_value = None
    # Default contact returned when a capture is saved
    mock.build_contact.return_value = ContactExtract(display_name="Test Contact")

    # Routers imported get_llm, so replace their copy
    monkeypatch.setattr("backend.routers.recall.get_llm", lambda: mock)
    monkeypatch.setattr("backend.routers.captures.get_llm", lambda: mock)
    return mock


@pytest.fixture
def embedder(monkeypatch):
    """
    Mock embedder returning deterministic vectors

    A fixed return_value would give every contact the same vector. 
    Set `embedder.embed_text.side_effect = RuntimeError(...)` to simulate the model being unavailable.
    """
    from backend.ai.embeddings.bge import BGEEmbedder

    # A mock with BGEEmbedder's methods
    mock = create_autospec(BGEEmbedder, instance=True)
    # Each text gets a fixed vector from its topic words, so ranking is predictable
    mock.embed_text.side_effect = topic_vector

    # Routers imported get_embedder, so replace their copy
    monkeypatch.setattr("backend.routers.recall.get_embedder", lambda: mock)
    monkeypatch.setattr("backend.routers.contacts.get_embedder", lambda: mock)
    return mock


@pytest.fixture
def client(db, llm, embedder) -> TestClient:
    """An anonymous API client to not load the real models."""
    from backend.main import app

    return TestClient(app)


@pytest.fixture
def make_user(client):
    """Register a user and return a client holding their session cookie."""
    from backend.main import app

    def _make_user(email: str, password: str = "password123") -> TestClient:
        user_client = TestClient(app)
        response = user_client.post("/auth/register", json={"email": email, "password": password})
        assert response.status_code == 200, response.text
        return user_client

    return _make_user

# Create the test users and return a client holding their session cookie
@pytest.fixture
def alice(make_user) -> TestClient:
    return make_user("alice@test.com")


@pytest.fixture
def bob(make_user) -> TestClient:
    return make_user("bob@test.com")