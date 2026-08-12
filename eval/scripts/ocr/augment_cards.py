"""
Augment business-card images for OCR model evaluation dataset

Applied transformations: low resolution (lowres), perspective distortion (warp), and both (warp_lowres).

Blocks IDs in ocr.jsonl:
    1-30    raw
    31-60   lowres
    61-90   warp
    91-120  warp_lowres

Usage
    python eval/scripts/ocr/augment_cards.py
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

# Define paths
REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "eval" / "datasets" / "images" / "raw"
OUT_DIR = REPO_ROOT / "eval" / "datasets" / "images" / "augmented"
GT_PATH = REPO_ROOT / "eval" / "datasets" / "ground_truths" / "ocr.jsonl"

# Locate each block's first ID in ocr.jsonl
BLOCKS = {"raw": 1, "lowres": 31, "warp": 61, "warp_lowres": 91}

# Define generated blocks (conditions)
GENERATED = ("lowres", "warp", "warp_lowres")

# Controls how much the JPEG compression algorithm degrades the image quality
JPEG_QUALITY = 92
# Controls the physical size of the image in pixels
TARGET_LOWRES = 640

# Define warp jitter for perspective distortion
WARP_JITTER = 0.12
# Define border fill for perspective distortion (light grey colour)
BORDER_FILL = (240.0, 240.0, 240.0)
# Define random seed for reproducibility
RANDOM_SEED = 42

def warp(img: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """
    Apply perspective distortion by randomly shifting corner positions.
    
    Simulates a photo taken at an angle by jittering each corner outward from its original position.
    Uses random seed for reproducibility.
    """
    h, w = img.shape[:2]

    # Source corners: top-left, top-right, bottom-right, bottom-left
    src = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
    
    # Calculate max jitter distance
    jx, jy = WARP_JITTER * w, WARP_JITTER * h
    
    # Create destination corners by randomly shifting each corner outward by random amount
    dst = src.copy()
    
    for i, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        # Shift x toward centre by a random amount in [0, jx]
        dst[i, 0] = np.clip(src[i, 0] + rng.uniform(0, jx) * sx, 0, w - 1)
        # Shift y toward centre by a random amount in [0, jy]
        dst[i, 1] = np.clip(src[i, 1] + rng.uniform(0, jy) * sy, 0, h - 1)

    # Perspective matrix from source to destination corners
    matrix = cv2.getPerspectiveTransform(src, dst.astype(np.float32))
    
    # Apply transformation and fill any empty borders with light grey colour
    return cv2.warpPerspective(
        img, matrix, (w, h), flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT, borderValue=BORDER_FILL,
    )


def downscale(img: np.ndarray, long_side: int) -> np.ndarray:
    """
    Resize image so the longest dimension equals long_side while maintaining aspect ratio.
    If image is already smaller than long_side, return original unchanged.
    """
    h, w = img.shape[:2]
    
    # Calculate scaling factor based on target longest dimension
    scale = long_side / max(h, w)
    
    # If image is already smaller than target longest dimension, return original unchanged
    if scale >= 1:
        return img
    
    # Calculate new dimensions maintaining aspect ratio
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    
    # Use INTER_AREA for best quality downscaling
    return cv2.resize(img, size, interpolation=cv2.INTER_AREA)


def get_card_id(path: Path) -> int:
    """
    Extract card id from filename (e.g., 'ocr_060.jpg' becomes 60).
    """
    # Extract all digit characters from filename (without extension)
    digits = "".join(c for c in path.stem if c.isdigit())
    
    # Ensure at least one digit was found
    if not digits:
        raise ValueError(f"no digits in {path.name}")
    
    # Remove leading zeros and convert to int
    return int(digits)


def load_raw_rows(path: Path) -> list[dict]:
    """
    Load a JSONL file and return only rows with condition='raw'.
    """
    rows = []
    
    # Read file line by line
    for line in path.read_text(encoding="utf-8").splitlines():
        # Skip empty lines
        if not line.strip():
            continue

        # Parse JSON and keep raw condition only
        row = json.loads(line)
        if row.get("condition") == "raw":
            rows.append(row)
    
    return rows


def main() -> None:
    """
    Main augmentation pipeline
    
    Steps:
    1. Find all raw images in the raw directory
    2. Load raw ground truth rows from ocr.jsonl
    3. Create lowres, warp, and warp_lowres images (and row metadata)
    4. Rebuild ocr.jsonl from raw rows + generated rows
    """
    # Step 1: Find all image files in the raw directory (list of Path objects)
    raw_images = sorted(
        p for p in RAW_DIR.iterdir()
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if not raw_images:
        raise SystemExit(f"no images in {RAW_DIR}")

    # Step 2: Load raw ground truth rows
    raw_rows = load_raw_rows(GT_PATH)
    if not raw_rows:
        raise SystemExit(f"no raw rows in {GT_PATH}")
    
    # Build lookup: card id to its ground truth text
    gt = {int(r["id"]): r["ground_truth"] for r in raw_rows}
    
    # Verify every image has a ground truth text
    missing = [get_card_id(p) for p in raw_images if get_card_id(p) not in gt]
    if missing:
        raise SystemExit(f"no ground truth text for cards: {missing}")

    # Step 3: Create augmented images and row metadata
    for cond in GENERATED:
        (OUT_DIR / cond).mkdir(parents=True, exist_ok=True)

    # Set JPEG encoding parameters
    encode = [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
    generated: list[dict] = []

    # Process each raw image and generate augmented versions
    for path in raw_images:
        card_id = get_card_id(path)
        
        # Load image in colour mode
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            raise SystemExit(f"could not read {path}")

        # Create RNG for reproducible warping that is unique for each card id
        rng = np.random.default_rng(RANDOM_SEED + card_id)
        
        # Apply warp transformation
        warped = warp(img, rng)
        
        # Generate all three augmented versions
        outputs = {
            "lowres": downscale(img, TARGET_LOWRES),
            "warp": warped,
            "warp_lowres": downscale(warped, TARGET_LOWRES),
        }

        # Write each augmented image and record its ground-truth row
        for cond, out_img in outputs.items():
            dest = OUT_DIR / cond / f"{path.stem}.jpg"
            if not cv2.imwrite(str(dest), out_img, encode):
                raise SystemExit(f"failed to write {dest}")

            # Add metadata for this augmented image to the list
            generated.append({
                "id": BLOCKS[cond] + card_id - 1,
                "condition": cond,
                "image": f"eval/datasets/images/augmented/{cond}/{path.stem}.jpg",
                "ground_truth": gt[card_id],
            })

    # Step 4: Combine raw and generated rows, sort by id, write ocr.jsonl
    rows = sorted(raw_rows + generated, key=lambda r: r["id"])
    GT_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    print("Successfully augmented cards.")


if __name__ == "__main__":
    main()