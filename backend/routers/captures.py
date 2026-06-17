from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from backend.dependencies import get_current_user
from backend.models import User
from backend.ai.asr.faster_whisper import get_asr
from backend.ai.ocr.easyocr import get_ocr

# Define the prefix and tags for the captures router
router = APIRouter(prefix="/captures", tags=["captures"])

# Max file upload sizes
MAX_AUDIO_SIZE = 10 * 1024 * 1024 # 10MB
MAX_IMAGE_SIZE = 25 * 1024 * 1024 # 25MB


@router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Transcribe an audio file to text.
    """
    # Validate file size
    audio_bytes = await file.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Audio file too large. Max 10MB.",
        )

    # Validate file type
    allowed_types = {"audio/wav", "audio/mpeg", "audio/mp4", "audio/webm", "audio/ogg"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio format: {file.content_type}",
        )

    # Transcribe the audio file to text
    try:
        asr = get_asr()
        transcript = asr.transcribe(audio_bytes, file.filename or "audio.webm")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )

    return {
        "transcript": transcript
    }


@router.post("/ocr")
async def ocr_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """
    Extract text from an image.
    """
    # Validate file size
    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image file too large. Max 25MB.",
        )

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image format: {file.content_type}",
        )

    # Extract text from the image
    try:
        ocr = get_ocr()
        text = ocr.extract_text(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR failed: {str(e)}",
        )

    return {
        "text": text
    }