"""
OCR model runners for evaluation (EasyOCR, RapidOCR, PaddleOCR).

Each run_* function:
    1. Load the model once
    2. Run OCR on every image path
    3. Unload the model

Result row shape (per image):
    {"raw_text": str, "latency_ms": float | None, "error": str | None}

Used by
    eval/scripts/run_ocr_eval.py
"""

from __future__ import annotations

import time
from pathlib import Path


def join_blocks(blocks) -> str:
    """
    Strip each text block (recognised text region), drop empties, and join with newlines.
    """
    # Strip whitespace and drop empty blocks
    cleaned: list[str] = []
    for block in blocks:
        text = str(block).strip()
        if text:
            cleaned.append(text)

    # Join blocks into a single string
    return "\n".join(cleaned)


def run_ocr_one(extract, path: Path) -> dict:
    """
    Run OCR model on a single image

    Returns a dict with raw_text, latency_ms (milliseconds), and optional error.
    """
    # Handle missing file (skip OCR run)
    if not path.is_file():
        return {
            "raw_text": "",
            "latency_ms": None,
            "error": f"missing image: {path}",
        }

    # Start timer
    t0 = time.perf_counter()
    try:
        text = extract(path)
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return {"raw_text": text, "latency_ms": ms, "error": None}

    except Exception as exc:
        # OCR failed, store error
        ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "raw_text": "",
            "latency_ms": ms,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_ocr_all(name: str, extract, image_paths: list[Path]) -> list[dict]:
    """
    Run the selected OCR model to all image paths by calling the extract function
    Prints progress every 10 images (and on the last).
    """
    results: list[dict] = []
    total = len(image_paths)

    # Run OCR on each image
    for i, path in enumerate(image_paths, start=1):
        results.append(run_ocr_one(extract, path))

        # Log progress every 10 images
        if i % 10 == 0 or i == total:
            print(f"  [{name}] {i}/{total}")

    return results


def run_easyocr(image_paths: list[Path]) -> list[dict]:
    """
    Load EasyOCR once, run on all image paths, then unload when the function returns.
    """
    import warnings

    import easyocr

    # Hide warning from EasyOCR/torch setting
    warnings.filterwarnings(
        "ignore",
        message=".*pin_memory.*not supported on MPS.*",
        category=UserWarning,
    )

    print("Loading EasyOCR...")
    # Loaded once and reused for every image in this batch
    # Reference: https://pypi.org/project/easyocr/
    reader = easyocr.Reader(["en"], gpu=False)
    print("EasyOCR ready.")

    def extract(path: Path) -> str:
        # Output only the text blocks without boxes or scores
        blocks = reader.readtext(str(path), detail=0)
        return join_blocks(blocks)

    # Run EasyOCR on all images
    return run_ocr_all("easyocr", extract, image_paths)


def run_rapidocr(image_paths: list[Path]) -> list[dict]:
    """
    Load RapidOCR once, run on all image paths, then unload when the function returns.
    """
    from rapidocr_onnxruntime import RapidOCR

    print("Loading RapidOCR...")
    # Loaded once and reused for every image in this batch
    # Reference: https://github.com/rapidai/rapidocr
    engine = RapidOCR()
    print("RapidOCR ready.")

    def extract(path: Path) -> str:
        # Extract the result from OCR
        result, _elapse = engine(str(path))
        if not result:
            return ""
        # Join the text blocks (element at index 1) into a single string
        return join_blocks(row[1] for row in result)

    # Run RapidOCR on all images
    return run_ocr_all("rapidocr", extract, image_paths)


def run_paddleocr(image_paths: list[Path]) -> list[dict]:
    """
    Load PaddleOCR once, run on all image paths, then unload when the function returns.
    """
    import os

    # Disable model source check for faster loading
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

    from paddleocr import PaddleOCR

    print("Loading PaddleOCR...")
    # Loaded once and reused for every image in this batch
    # Reference: https://www.paddleocr.ai/main/en/quick_start.html
    engine = PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        engine="paddle",
    )
    print("PaddleOCR ready.")

    def extract(path: Path) -> str:
        # Collect recognition text strings only (no boxes / scores)
        results = engine.predict(str(path))
        if not results:
            return ""

        blocks: list[str] = []
        for result in results:
            rec_texts = result["rec_texts"] if "rec_texts" in result else None
            if rec_texts:
                blocks.extend(str(t) for t in rec_texts)

        return join_blocks(blocks)

    # Run PaddleOCR on all images
    return run_ocr_all("paddleocr", extract, image_paths)


# Map CLI model names to load-once runners
MODELS = {
    "easyocr": run_easyocr,
    "rapidocr": run_rapidocr,
    "paddleocr": run_paddleocr,
}