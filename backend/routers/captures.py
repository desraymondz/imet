from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.dependencies import get_current_user
from backend.models import User
from backend.ai.asr.faster_whisper import get_asr

# Define the prefix and tags for the captures router
router = APIRouter(prefix="/captures", tags=["captures"])

# Max 25MB audio file
MAX_AUDIO_SIZE = 25 * 1024 * 1024


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
            detail="Audio file too large. Max 25MB.",
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
        transcript = asr.transcribe(audio_bytes, file.filename)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Transcription failed: {str(e)}",
        )

    return {
        "transcript": transcript
    }