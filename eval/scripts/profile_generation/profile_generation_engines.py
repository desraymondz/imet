"""
Profile-generation model runners for evaluation (Qwen3.5 via Ollama).

Models:
    qwen3.5_4b
    qwen3.5_2b
    qwen3.5_0.8b

Each run:
    1. Connect to Ollama (model already pulled)
    2. Run contact extraction on every ground-truth input
    3. Return when the batch finishes

Result row shape (per capture input):
    {
        "prediction": {
            "display_name", "email", "phone", "company", "role",
            "location", "profile_text", "keywords"
        },
        "latency_ms": float | None,
        "error": str | None,
    }

Prompt and schema match backend/ai/llm/ollama.py build_contact.

Used by
    eval/scripts/profile_generation/run_profile_eval.py
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

# Flat JSON schema passed to Ollama format=... for structured contact output
# Same schema as CONTACT_OLLAMA_SCHEMA in backend/ai/llm/ollama.py
CONTACT_OLLAMA_SCHEMA = {
    "type": "object",
    "properties": {
        "display_name": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "company": {"type": "string"},
        "role": {"type": "string"},
        "location": {"type": "string"},
        "profile_text": {"type": "string"},
        "keywords": {"type": "array", "items": {"type": "string"}},
    },
}

# Clean up for messy LLM responses when the model doesn't know a field
_NULL_STRINGS = {"", "null", "none", "unknown", "n/a"}

# Empty ContactExtract shaped prediction used on skip / parse failures
_EMPTY_PREDICTION: dict[str, Any] = {
    "display_name": None,
    "email": None,
    "phone": None,
    "company": None,
    "role": None,
    "location": None,
    "profile_text": None,
    "keywords": None,
}

# Model name maps to Ollama tag name (since colons are invalid in filenames)
OLLAMA_TAGS = {
    "qwen3.5_4b": "qwen3.5:4b",
    "qwen3.5_2b": "qwen3.5:2b",
    "qwen3.5_0.8b": "qwen3.5:0.8b",
}


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


def _normalise_prediction(data: dict) -> dict[str, Any]:
    """
    Normalise raw LLM JSON into a ContactExtract shaped prediction dict.
    Removes whitespace and converts null-like strings to None.
    """
    normalised: dict[str, Any] = {}

    # Iterate over every field in the expected prediction shape
    for field in _EMPTY_PREDICTION:
        value = data.get(field)

        # Handle keywords field
        if field == "keywords":
            # Check if keywords' value is a list
            if isinstance(value, list):
                # Strip each item and drop empty entries
                keywords = [
                    item.strip()
                    for item in value
                    if isinstance(item, str) and item.strip()
                ]
                # Empty list becomes None
                normalised[field] = keywords or None
            else:
                # When keywords' value is not a list, set to None
                normalised[field] = None
            continue

        # Handle string fields
        if isinstance(value, str):
            # Remove whitespace
            cleaned = value.strip()
            # Convert null-like strings to None
            normalised[field] = None if cleaned.lower() in _NULL_STRINGS else cleaned
        else:
            normalised[field] = value

    return normalised


def _parse_contact_response(response: str) -> dict[str, Any]:
    """
    Parse and normalise a contact JSON response from the LLM.

    Steps:
    1. Strip markdown fences if present
    2. Reject empty responses
    3. Parse JSON
    4. Return the normalised prediction dict
    """
    # Step 1: Strip markdown fences
    cleaned = _strip_json_fences(response)

    # Step 2: Reject empty responses
    if cleaned.strip() in ("", "{}", "{ }"):
        raise ValueError("LLM returned empty JSON object")

    # Step 3: Parse JSON
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM response is not a JSON object")

    # Step 4: Normalise field values
    return _normalise_prediction(data)


def build_prompt(
    ocr_text: str | None,
    asr_text: str | None,
    freeform_text: str | None,
) -> str | None:
    """
    Build the contact-extraction prompt from GT input fields.

    Same prompt as the main app (backend/ai/llm/ollama.py build_contact)

    Steps:
    1. Collect non-empty input blocks (ASR, OCR, free-form)
    2. Return None if nothing usable
    3. Join blocks and build the full prompt
    """
    inputs: list[str] = []

    # Step 1: Collect non-empty input blocks
    # ASR (voice note transcript)
    if asr_text and asr_text.strip():
        inputs.append(f"Voice note transcript:\n{asr_text.strip()}")

    # OCR image text
    if ocr_text and ocr_text.strip():
        inputs.append(
            f"Image text (business card):\n{ocr_text.strip()}"
        )

    # Free-form notes
    if freeform_text and freeform_text.strip():
        inputs.append(f"Free-form notes:\n{freeform_text.strip()}")

    # Step 2: Return None if no blocks is usable
    if not inputs:
        return None

    # Step 3: Join blocks and build the full prompt
    inputs_block = "\n\n".join(inputs)

    return f"""You are helping someone remember a person they just met.

Extract a contact profile with these fields:
- display_name: full name, or empty string if unknown
- email: email address, or empty string if unknown
- phone: phone number, or empty string if unknown
- company: company or organisation, or empty string if unknown
- role: job title or role, or empty string if unknown
- location: city, country, or address, or empty string if unknown
- profile_text: a warm, natural 2-3 sentence summary of who this person is.
  Write it like a memory aid, include their role, company, and any interesting personal details mentioned in the inputs.
- keywords: short lowercase tags (industry, role, interests, traits)

Use image text mainly for structured fields (name, email, phone, company, role, location).
Use the voice note mainly for personal context, interests, and profile_text.
Use free-form notes mainly to fill gaps or add context when the other sources are sparse.
If multiple sources mention the same field, prefer image text for structured fields,
unless the voice note or free-form notes clearly say the card is out of date.
Do not invent facts not present in the input.
Respond with valid JSON only. Use empty strings for unknown fields.

Example:
Voice note transcript:
Met Jane Doe at the design meetup. She leads product design at Acme Labs. Really into trail running, did the Three Peaks last year.

Image text (business card):
JANE DOE
Product Designer
Acme Labs
jane@acme.example
+44 7700 900123
Manchester

Free-form notes:
intro via Sam. Follow up about the portfolio review

Output:
{{"display_name": "Jane Doe", "email": "jane@acme.example", "phone": "+44 7700 900123", "company": "Acme Labs", "role": "Product Designer", "location": "Manchester", "profile_text": "Product designer at Acme Labs in Manchester. Keen trail runner who completed the Three Peaks last year. Met at the design meetup; introduced by Sam and worth following up about a portfolio review.", "keywords": ["product design", "trail running", "acme labs"]}}

Now extract a contact profile from this information:

{inputs_block}
"""


def run_profile_one(generate, capture_input: dict) -> dict:
    """
    Run profile generation on a single capture input dict.
    Returns a dict with prediction, latency_ms, and optional error.
    """
    # Build the prompt from the three optional input sources
    prompt = build_prompt(
        capture_input.get("ocr_text"),
        capture_input.get("asr_text"),
        capture_input.get("freeform_text"),
    )

    # Handle no usable input
    if prompt is None:
        # Return empty prediction
        return {
            "prediction": dict(_EMPTY_PREDICTION),
            "latency_ms": None,
            "error": None,
        }

    # Start timer for single-call LLM latency
    t0 = time.perf_counter()
    try:
        # Call the model-specific generate function
        prediction = generate(prompt)
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {"prediction": prediction, "latency_ms": latency_ms, "error": None}

    except Exception as exc:
        # Generation / parse failed will store empty prediction and error
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "prediction": dict(_EMPTY_PREDICTION),
            "latency_ms": latency_ms,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_profile_all(name: str, generate, capture_inputs: list[dict]) -> list[dict]:
    """
    Run profile generation on all capture inputs.
    Prints progress every 10 capture inputs (and on the last).
    """
    results: list[dict] = []
    total = len(capture_inputs)

    # Run profile generation on each capture input
    for i, capture_input in enumerate(capture_inputs, start=1):
        results.append(run_profile_one(generate, capture_input))

        # Log progress every 10 capture inputs
        if i % 10 == 0 or i == total:
            print(f"  [{name}] {i}/{total}")

    return results


def _make_ollama_generate(ollama_tag: str):
    """
    Build a generate(prompt) function for one Ollama model.
    Eval calls the model once with a structured schema (no JSON retry).
    """
    from ollama import Client

    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    # Client is reused for every capture input
    client = Client(host=host)

    def generate(prompt: str) -> dict[str, Any]:
        # Build chat messages (same as main app)
        messages = [{"role": "user", "content": prompt}]

        # Call Ollama chat completion once with structured schema
        # Reference: https://github.com/ollama/ollama/blob/main/docs/api.md
        # think=False disables Qwen "thinking" tokens for faster structured JSON
        response = client.chat(
            model=ollama_tag,
            messages=messages,
            format=CONTACT_OLLAMA_SCHEMA,
            think=False,
            options={"temperature": 0.1},
        )
        content = response.message.content or ""

        # Parse and normalise into prediction dict
        return _parse_contact_response(content)

    return generate


def run_ollama_model(cli_name: str, capture_inputs: list[dict]) -> list[dict]:
    """
    Run one Ollama model (by CLI name) on all capture inputs.
    Looks up the Ollama tag from OLLAMA_TAGS, connects once, then runs the batch.
    """
    tag = OLLAMA_TAGS[cli_name]
    print(f"Using Ollama model {tag}...")
    # Builds a ready-to-call function for calling the Ollama model
    generate = _make_ollama_generate(tag)
    print(f"{tag} ready.")
    # Run on every capture input in the batch
    return run_profile_all(cli_name, generate, capture_inputs)