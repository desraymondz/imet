"""
Score predicted profile_text with an Anthropic LLM-as-a-judge.

Pipeline (one model at a time):
    1. Load ground-truth rows from profile_generation.jsonl
    2. Load predictions from eval/predictions/profile_generation/{model}.jsonl
    3. Join by id and ask Claude for a binary pass/fail on profile_text
    4. Write eval/judgements/profile_generation/{model}.jsonl (overwrites if present)

Judgement row fields:
    id, model, pass, error

Usage
    python eval/scripts/profile_generation/run_profile_judge.py --model qwen3.5_0.8b
    python eval/scripts/profile_generation/run_profile_judge.py --model qwen3.5_2b
    python eval/scripts/profile_generation/run_profile_judge.py --model qwen3.5_4b
    python eval/scripts/profile_generation/run_profile_judge.py --model all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from profile_generation_engines import OLLAMA_TAGS

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]
GT_PATH = REPO_ROOT / "eval" / "datasets" / "ground_truths" / "profile_generation.jsonl"
PRED_DIR = REPO_ROOT / "eval" / "predictions" / "profile_generation"
JUDGE_DIR = REPO_ROOT / "eval" / "judgements" / "profile_generation"

# Import the shared Anthropic client
sys.path.insert(0, str(REPO_ROOT / "eval" / "scripts" / "llm_judge"))
from anthropic_judge import judge

# Rubric (system prompt for judge model)
RUBRIC = """
You are scoring a contact memory-aid summary (profile_text).

Return JSON only: {"pass": true} or {"pass": false}

Rules:
- Fail if the prediction invents a fact that is not in the capture (OCR / voice note / notes).
- Fail if the prediction drops a fact that is in the expected profile_text. Paraphrase is OK.
- Do not require email, phone, or URLs unless they appear in the expected profile_text.
- Extra true details from the capture that the expected summary omitted are not a fail.
- Ignore wording, warmth, and sentence count.
"""


def load_jsonl(path: Path) -> list[dict]:
    """
    Load rows from a JSONL file then convert into a list of dictionaries
    """
    rows: list[dict] = []

    # Read file line by line
    for line in path.read_text(encoding="utf-8").splitlines():
        # Skip empty lines
        if not line.strip():
            continue
        # Parse JSON and add to list
        rows.append(json.loads(line))

    return rows


def _format_capture_input(capture_input: dict) -> str | None:
    """
    Format OCR / ASR / free-form notes for the judge prompt.
    Returns None if nothing usable.
    """
    blocks: list[str] = []

    # Pull each source and drop whitespace-only values
    ocr_text = (capture_input.get("ocr_text") or "").strip()
    asr_text = (capture_input.get("asr_text") or "").strip()
    freeform_text = (capture_input.get("freeform_text") or "").strip()

    # Keep the same labels and order as build_prompt (ASR, OCR, notes)
    if asr_text:
        blocks.append(f"Voice note transcript:\n{asr_text}")
    if ocr_text:
        blocks.append(f"Image text (business card):\n{ocr_text}")
    if freeform_text:
        blocks.append(f"Free-form notes:\n{freeform_text}")

    # Nothing usable in the capture
    if not blocks:
        return None

    return "\n\n".join(blocks)


def build_user_prompt(
    capture_block: str,
    expected_profile_text: str,
    predicted_profile_text: str,
) -> str:
    """
    Build the user prompt with capture input block, expected profile_text, predicted profile_text.
    """
    return f"""
Capture:
{capture_block}

Expected profile_text:
{expected_profile_text}

Predicted profile_text:
{predicted_profile_text}
"""


def judge_one(gt_row: dict, pred_row: dict) -> dict:
    """
    Score one predicted profile_text.

    Steps:
    1. Skip if the prediction errored, profile_text is empty, or capture is empty
    2. Call the Anthropic judge
    3. Check for pass value in the judge response
    """
    prediction = pred_row.get("prediction") or {}
    profile_text = prediction.get("profile_text")
    pred_error = pred_row.get("error")

    # Step 1: Skip unusable predictions capture input
    if pred_error:
        return {"pass": None, "error": f"prediction error: {pred_error}"}
    if not isinstance(profile_text, str) or not profile_text.strip():
        return {"pass": None, "error": "empty profile_text"}

    capture_block = _format_capture_input(gt_row["input"])
    if capture_block is None:
        return {"pass": None, "error": "empty capture"}

    expected = (gt_row.get("expected") or {}).get("profile_text") or ""

    # Step 2: Call the judge
    try:
        result = judge(
            RUBRIC,
            build_user_prompt(capture_block, expected, profile_text.strip()),
        )
    except Exception as exc:
        return {"pass": None, "error": f"{type(exc).__name__}: {exc}"}

    # Step 3: Check for pass value in the judge response
    pass_value = result.get("pass")
    if not isinstance(pass_value, bool):
        return {"pass": None, "error": f"judge did not return boolean pass: {result}"}

    return {"pass": pass_value, "error": None}


def judge_model(model: str, gt_rows: list[dict]) -> None:
    """
    Judge one model's predictions and write judgement JSONL.

    Steps:
    1. Validate the CLI model name
    2. Load model's prediction file
    3. Join GT with predictions by id
    4. Score each row and write judgements/profile_generation/{model}.jsonl
    """
    # Step 1: Validate the CLI model name
    if model not in OLLAMA_TAGS:
        known = ", ".join(OLLAMA_TAGS)
        raise SystemExit(f"Unknown model '{model}'. Choose one of: {known}")

    # Step 2: Load the predictions file
    pred_path = PRED_DIR / f"{model}.jsonl"
    if not pred_path.is_file():
        raise SystemExit(f"Missing predictions file: {pred_path}")

    pred_rows = load_jsonl(pred_path)
    pred_by_id = {row["id"]: row for row in pred_rows}

    # Ensure output directory exists for the judgements file
    JUDGE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = JUDGE_DIR / f"{model}.jsonl"

    # Step 3 and 4: Join by id, score each, then write to file
    total = len(gt_rows)
    with out_path.open("w", encoding="utf-8") as fh:
        for i, gt_row in enumerate(gt_rows, start=1):
            row_id = gt_row["id"]
            pred_row = pred_by_id.get(row_id)

            # Missing prediction for this GT id
            if pred_row is None:
                record = {
                    "id": row_id,
                    "model": model,
                    "pass": None,
                    "error": "missing prediction",
                }
            else:
                judged = judge_one(gt_row, pred_row)
                record = {
                    "id": row_id,
                    "model": model,
                    "pass": judged["pass"],
                    "error": judged["error"],
                }

            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

            # Log progress every 10 capture inputs
            if i % 10 == 0 or i == total:
                print(f"  [{model}] {i}/{total}")

    print(f"Wrote {total} rows to: {out_path.relative_to(REPO_ROOT)}")


def main() -> None:
    """
    Main profile-text judge pipeline.

    Steps:
    1. Parse CLI argument --model
    2. Load ground-truth rows
    3. Judge the selected models one at a time
    """
    # Step 1: Parse CLI argument --model
    parser = argparse.ArgumentParser(description="Run profile-text LLM-as-a-judge")
    parser.add_argument(
        "--model",
        required=True,
        help="qwen3.5_4b | qwen3.5_2b | qwen3.5_0.8b | all",
    )
    args = parser.parse_args()

    # Step 2: Load ground truth rows
    gt_rows = load_jsonl(GT_PATH)
    if not gt_rows:
        raise SystemExit(f"No rows in {GT_PATH}")

    # Handle which models to run (one at a time)
    model = args.model.strip().lower()
    if model == "all":
        models = list(OLLAMA_TAGS.keys())
    else:
        models = [model]

    # Step 3: Judge the selected models one at a time
    print(f"Judging {len(models)} model(s) on {len(gt_rows)} capture inputs")
    for model in models:
        print(f"Judging {model}...")
        judge_model(model, gt_rows)
        print(f"Finished judging {model}.")


if __name__ == "__main__":
    main()
