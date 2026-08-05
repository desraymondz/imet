import tempfile
import os
from faster_whisper import WhisperModel

WHISPER_MODEL_SIZE = "base"


class FasterWhisperASR:
    def __init__(self):
        # Loaded at startup, reused across requests
        # Reference: https://pypi.org/project/faster-whisper/
        print("Loading Whisper model...")
        self.model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device="cpu",
            compute_type="int8",
        )
        print("Whisper model loaded successfully")

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        """
        Transcribe the audio bytes to text:
        1. Create a temp file and on disk so that Whisper can read it
        2. Transcribe the audio file to text
        3. Delete the temp file after transcribing
        """
        # Get the extension of the audio file
        extension = os.path.splitext(filename)[-1]
        if not extension:
            raise ValueError("Audio filename must include an extension (e.g. .webm)")

        # Write the audio bytes to a temp file on disk
        # Reference: https://docs.python.org/3/library/tempfile.html
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            # Transcribe the audio file to text in english
            segments, _ = self.model.transcribe(tmp_path, language="en")
            # Join the segments into a single string
            return " ".join(segment.text.strip() for segment in segments)
        finally:
            # Clean up temp file after transcribing
            os.unlink(tmp_path)


# Shared ASR instance
_asr: FasterWhisperASR | None = None


def get_asr() -> FasterWhisperASR:
    """Return the shared ASR instance."""
    global _asr
    if _asr is None:
        # Create the ASR instance
        _asr = FasterWhisperASR()
    return _asr