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
For recall eval seed scripts, set `EVAL_DATABASE_URL` host to `localhost` (database `imet_eval` on the same Postgres).

**Ollama (local LLM):**

Start the Ollama server, then pull models separately before first use (must match `OLLAMA_MODEL_FAST` / `OLLAMA_MODEL_QUALITY` in `.env.local`):

```bash
ollama serve
ollama pull qwen3.5:0.8b
```

If you change the model in `.env.local`, pull that model too, e.g. `ollama pull llama3.2:3b`.

**Embeddings (recall / semantic search):**

The API loads `BAAI/bge-base-en-v1.5` via sentence-transformers at startup. On first run, the model is downloaded automatically (~400MB). Expect ~500MB+ extra RAM while the API is running. Override with `EMBEDDING_MODEL` in `.env.local` if needed.

## Run

**Database (Docker):**

```bash
docker compose -f compose.dev.yml --env-file .env.local up postgres -d
```

**Eval database (recall seed):**

Same Postgres instance, separate database `imet_eval`. The script creates it if missing, loads `eval/datasets/recall/contacts.jsonl`, and embeds `profile_text` with the same BGE model as the API. Re-running replaces the seeded contacts.

```bash
uv run python eval/scripts/recall/seed_eval_db.py
```

**API (local):**

```bash
uv run uvicorn backend.main:app --reload
```

- API: http://localhost:8000
- Docs: http://localhost:8000/docs

**LLM (local):**

```bash
ollama serve
```

**Full stack (Docker):**

```bash
docker compose -f compose.dev.yml --env-file .env.local up --build
```
