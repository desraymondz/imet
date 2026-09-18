import os
import tempfile

# Disable model source check for faster loading
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from paddleocr import PaddleOCR as _PaddleOCREngine


def _image_suffix(image_bytes: bytes) -> str:
    """
    Return the temp-file extension from magic bytes.
    """
    # Reference: https://stackoverflow.com/questions/4550296/how-to-identify-contents-of-a-byte-is-a-jpeg
    if image_bytes.startswith(b"\x89PNG"):
        return ".png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    # Reference: https://developers.google.com/speed/webp/docs/riff_container
    if len(image_bytes) >= 12 and image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
        return ".webp"
    return ".jpg"


class PaddleOCR:
    def __init__(self):
        # Loaded at startup, reused across requests
        # Reference: https://www.paddleocr.ai/main/en/quick_start.html
        print("Loading PaddleOCR model...")
        self.engine = _PaddleOCREngine(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            engine="paddle",
        )
        print("PaddleOCR model loaded successfully")

    def extract_text(self, image_bytes: bytes) -> str:
        """
        Run OCR on image bytes and return detected text:
        1. Write bytes to a temp file so PaddleOCR can read a path
        2. Extract text blocks from the image
        3. Join blocks into a single string for LLM processing later
        """
        # Write the image bytes to a temp file on disk
        # Reference: https://docs.python.org/3/library/tempfile.html
        with tempfile.NamedTemporaryFile(suffix=_image_suffix(image_bytes), delete=False) as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            results = self.engine.predict(tmp_path)
            if not results:
                return ""

            # Collect recognition text strings only
            cleaned_blocks: list[str] = []
            for result in results:
                # List of recognised strings
                rec_texts = result["rec_texts"] if "rec_texts" in result else None
                if not rec_texts:
                    continue
                # Strip whitespace and drop empty blocks
                for block in rec_texts:
                    cleaned = str(block).strip()
                    if cleaned:
                        cleaned_blocks.append(cleaned)

            # Join blocks into a single string for LLM processing later
            return "\n".join(cleaned_blocks)
        finally:
            # Clean up temp file after OCR
            os.unlink(tmp_path)


# Shared OCR instance
_ocr: PaddleOCR | None = None


def get_ocr() -> PaddleOCR:
    """Return the shared OCR instance."""
    global _ocr
    if _ocr is None:
        # Create the OCR instance
        _ocr = PaddleOCR()
    return _ocr