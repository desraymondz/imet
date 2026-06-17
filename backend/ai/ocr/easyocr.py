import easyocr

OCR_LANGUAGES = ["en"]


class EasyOCR:
    def __init__(self):
        # Loaded at startup, reused across requests
        # Reference: https://pypi.org/project/easyocr/
        print("Loading EasyOCR model...")
        self.reader = easyocr.Reader(OCR_LANGUAGES, gpu=False)
        print("EasyOCR model loaded successfully")

    def extract_text(self, image_bytes: bytes) -> str:
        """
        Run OCR on image bytes and return detected text:
        1. Extract text blocks from the image
        2. Join blocks into a single string for LLM processing later
        """
        # Returns a list of text blocks
        text_blocks = self.reader.readtext(image_bytes, detail=0)

        # Strip whitespace and drop empty blocks
        cleaned_blocks: list[str] = []
        for block in text_blocks:
            cleaned = block.strip()
            if cleaned:
                cleaned_blocks.append(cleaned)

        # Join blocks into a single string for LLM processing later
        return "\n".join(cleaned_blocks)


# Shared OCR instance
_ocr: EasyOCR | None = None


def get_ocr() -> EasyOCR:
    """Return the shared OCR instance."""
    global _ocr
    if _ocr is None:
        # Create the OCR instance
        _ocr = EasyOCR()
    return _ocr