"""
Anthropic LLM-as-a-judge client for evaluation.

Callers pass their own system / user prompts, then this module only:
    1. Load ANTHROPIC_API_KEY from environment variables
    2. Call Anthropic model (Haiku 4.5)
    3. Parse a JSON object from the response

Used by
    eval/scripts/profile_generation/run_profile_judge.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]

# Judge model (Claude API alias)
# Reference: https://platform.claude.com/docs/en/about-claude/models/overview
JUDGE_MODEL = "claude-haiku-4-5"


def _strip_json_fences(content: str) -> str:
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


def _parse_json_object(response: str) -> dict[str, Any]:
    """
    Parse an LLM response into a JSON object.

    Steps:
    1. Strip markdown fences
    2. Reject empty responses
    3. Return the parsed JSON dict
    """
    # Step 1: Strip markdown fences
    cleaned = _strip_json_fences(response)

    # Step 2: Reject empty responses
    if cleaned.strip() in ("", "{}", "{ }"):
        raise ValueError("Judge returned empty JSON object")

    # Step 3: Parse the first JSON object (Haiku often adds extra text after it)
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("Judge response has no JSON object")
    decoder = json.JSONDecoder()
    data, _end = decoder.raw_decode(cleaned[start:])
    if not isinstance(data, dict):
        raise ValueError("Judge response is not a JSON object")

    return data


def _load_api_key() -> str:
    """
    Load ANTHROPIC_API_KEY from the environment.
    """
    # Load environment variables from .env.local
    load_dotenv(REPO_ROOT / ".env.local")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key == "sk-anthropic-api-key-here":
        raise SystemExit(
            "ANTHROPIC_API_KEY is missing. Set it in .env.local"
        )

    return api_key


def judge(system: str, user: str) -> dict[str, Any]:
    """
    Call Claude once (plus one retry) and return the parsed JSON object.

    Parameters:
    - system: rubric
    - user: LLM response to be judged

    Steps:
    1. Load API key and build the Anthropic client
    2. Call the judge model
    3. Parse JSON. On parse failure, retry the same prompt once
    """
    from anthropic import Anthropic

    # Step 1: Load API key and build the client
    client = Anthropic(api_key=_load_api_key())

    def _call() -> str:
        # Send request to the judge model
        response = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=256,
            temperature=0,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Get the response text content
        parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        return "".join(parts)

    # Step 2: Call the judge model
    content = _call()
    try:
        # Step 3: Parse JSON
        return _parse_json_object(content)
    except (ValueError, json.JSONDecodeError):
        # One retry on parse failure
        content = _call()
        return _parse_json_object(content)