"""
Query-understanding model runners for evaluation.

Models:
    qwen3.5_4b
    qwen3.5_2b
    qwen3.5_0.8b

Each run:
    1. Connect to Ollama (model already pulled)
    2. Run query understanding on every ground-truth query
    3. Return when the batch finishes

Result row shape (per query):
    {
        "prediction": {
            "in_scope": bool,
            "keywords": list[str],
            "hyde_rewrite": str,
        },
        "latency_ms": float | None,
        "error": str | None,
    }

Prompt and schema match backend/ai/llm/ollama.py understand_recall_query.
Eval does not apply the in-scope empty-field fallback.

Used by
    eval/scripts/query_understanding/run_query_understanding_eval.py
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

# Flat JSON schema passed to Ollama for structured output
# Same schema as RECALL_QUERY_PLAN_OLLAMA_SCHEMA in backend/ai/llm/ollama.py
RECALL_QUERY_PLAN_OLLAMA_SCHEMA = {
    "type": "object",
    "properties": {
        "in_scope": {"type": "boolean"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "hyde_rewrite": {"type": "string"},
    },
    "required": ["in_scope", "keywords", "hyde_rewrite"],
}

# Empty plan used on skip / parse failures
EMPTY_PREDICTION: dict[str, Any] = {
    "in_scope": False,
    "keywords": [],
    "hyde_rewrite": "",
}

# Model name maps to Ollama tag name (since colons are invalid in filenames)
OLLAMA_TAGS = {
    "qwen3.5_4b": "qwen3.5:4b",
    "qwen3.5_2b": "qwen3.5:2b",
    "qwen3.5_0.8b": "qwen3.5:0.8b",
}


def strip_json_fences(content: str) -> str:
    """
    Remove markdown JSON fences (```json ... ```) from LLM response.
    """
    text = content.strip()

    # Return unchanged if not fenced
    if not text.startswith("```"):
        return text

    # Drop opening fence (```json or ```)
    text = text.removeprefix("```json").removeprefix("```").strip()

    # Drop closing fence
    if text.endswith("```"):
        text = text[:-3].strip()

    return text


def parse_keywords(raw_keywords: Any) -> list[str]:
    """
    Accept list[str], or a single string if the model slips (e.g. "hiking, outdoors").
    Same normalisation as production, without the empty-field fallback.
    """
    # If the keywords are a string, split on whitespace
    if isinstance(raw_keywords, str):
        return [token for token in raw_keywords.split() if token.strip()]

    # If the keywords are a list, keep non-empty strings
    if isinstance(raw_keywords, list):
        return [
            item.strip()
            for item in raw_keywords
            if isinstance(item, str) and item.strip()
        ]

    return []


def parse_in_scope(raw: Any) -> bool:
    """
    Parse in_scope from bool or common string forms.
    """
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in {"true", "1", "yes"}
    return bool(raw)


def parse_plan_response(response: str) -> dict[str, Any]:
    """
    Parse a query-plan JSON response from the LLM.

    Steps:
    1. Strip markdown fences
    2. Reject empty responses
    3. Parse JSON
    4. Return normalised in_scope, keywords, hyde_rewrite
    """
    # Step 1: Strip markdown fences
    cleaned = strip_json_fences(response)

    # Step 2: Reject empty responses
    if cleaned.strip() in ("", "{}", "{ }"):
        raise ValueError("LLM returned empty JSON object")

    # Step 3: Parse JSON
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a JSON object")

    # Step 4: Normalise fields
    hyde_rewrite = data.get("hyde_rewrite", "")
    if not isinstance(hyde_rewrite, str):
        hyde_rewrite = ""

    return {
        "in_scope": parse_in_scope(data.get("in_scope", False)),
        "keywords": parse_keywords(data.get("keywords", [])),
        "hyde_rewrite": hyde_rewrite.strip(),
    }


def build_prompt(query: str) -> str:
    """
    Build the query-understanding prompt.

    Same prompt as the main app (backend/ai/llm/ollama.py understand_recall_query)
    """
    cleaned_query = query.strip()
    return f"""You are a query planner for a personal contact network. The user is searching people they already know.

The user asked:
{cleaned_query}

Produce a query plan with:
- in_scope: true for any request to find a person in their network
  (who likes X, who works at Y, classmates, names). "who likes hiking" is in scope.
  false only for questions that are not about people they know
  (weather, math, coding help, news, general trivia).
- keywords: short lexical search terms as a JSON string array for full-text search
  (names, companies, roles, places, hobbies). Empty array if out of scope.
- hyde_rewrite: 1-2 sentences written like a contact profile_text that would match
  what they are looking for (Hypothetical Document Embedding). Empty string if out of scope.

Example in scope:
User asked: who likes hiking
Output:
{{"in_scope": true, "keywords": ["hiking", "outdoors"], "hyde_rewrite": "Enjoys hiking and outdoor activities. Often talks about trails and weekend mountain trips."}}

Example out of scope:
User asked: what's the weather in London tomorrow
Output:
{{"in_scope": false, "keywords": [], "hyde_rewrite": ""}}

Respond with valid JSON only.
"""


def run_query_one(generate, query: str) -> dict:
    """
    Run query understanding on a single query string.
    Returns a dict with prediction, latency_ms, and optional error.
    """
    # Handle empty query
    if not query.strip():
        return {
            "prediction": dict(EMPTY_PREDICTION),
            "latency_ms": None,
            "error": None,
        }

    # Start timer for single-call LLM latency
    t0 = time.perf_counter()
    try:
        # Call the model-specific generate function
        prediction = generate(query)
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {"prediction": prediction, "latency_ms": latency_ms, "error": None}

    except Exception as exc:
        # Generation / parse failed will store empty prediction and error
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "prediction": dict(EMPTY_PREDICTION),
            "latency_ms": latency_ms,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_query_all(name: str, generate, queries: list[str]) -> list[dict]:
    """
    Run query understanding on all queries.
    Prints progress every 10 queries (and on the last).
    """
    results: list[dict] = []
    total = len(queries)

    # Run query understanding on each query
    for i, query in enumerate(queries, start=1):
        results.append(run_query_one(generate, query))

        # Log progress every 10 queries
        if i % 10 == 0 or i == total:
            print(f"  [{name}] {i}/{total}")

    return results


def make_ollama_generate(ollama_tag: str):
    """
    Build a generate(query) function for one Ollama model.
    Eval calls the model once with a structured schema.
    """
    from ollama import Client

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    # Client is reused for every query
    client = Client(host=host)

    def generate(query: str) -> dict[str, Any]:
        # Build chat messages (same as main app)
        messages = [{"role": "user", "content": build_prompt(query)}]

        # Call Ollama chat completion once with structured schema
        # Reference: https://github.com/ollama/ollama/blob/main/docs/api.md
        # think=False disables Qwen "thinking" tokens for faster structured JSON
        response = client.chat(
            model=ollama_tag,
            messages=messages,
            format=RECALL_QUERY_PLAN_OLLAMA_SCHEMA,
            think=False,
            options={"temperature": 0.1},
        )
        content = response.message.content or ""

        # Parse into prediction dict (no empty-field fallback)
        return parse_plan_response(content)

    return generate


def run_ollama_model(cli_name: str, queries: list[str]) -> list[dict]:
    """
    Run one Ollama model (by CLI name) on all queries.
    Looks up the Ollama tag from OLLAMA_TAGS, connects once, then runs the batch.
    """
    tag = OLLAMA_TAGS[cli_name]
    print(f"Using Ollama model {tag}...")
    
    # Builds a ready-to-call function for calling the Ollama model
    generate = make_ollama_generate(tag)
    print(f"{tag} ready.")

    # Run on every query in the batch
    return run_query_all(cli_name, generate, queries)