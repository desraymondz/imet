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
