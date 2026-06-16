# iMet

iMet: A Multimodal AI for Personal Relationship Management PWA
> University of London CM3070 Final Project


## Setup

```bash
cp .env.example .env.local
# Update environments variable

uv sync
```

For local API dev, set `DATABASE_URL` host to `localhost` in `.env.local`.

## Run

**Database (Docker):**

```bash
docker compose -f compose.dev.yml --env-file .env.local up postgres -d
```

**API (local):**

```bash
uv run uvicorn backend.main:app --reload
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

**Full stack (Docker):**

```bash
docker compose -f compose.dev.yml --env-file .env.local up --build
```
