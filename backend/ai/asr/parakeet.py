import tempfile
import os
from parakeet_mlx import from_pretrained

class ParakeetASR:
    def __init__(self):
        # Loaded at startup, reused across requests
        # Reference: https://github.com/senstella/parakeet-mlx
        print("Loading Parakeet TDT 0.6B v3...")
        self.model = from_pretrained("mlx-community/parakeet-tdt-0.6b-v3")
        print("Parakeet TDT 0.6B v3 loaded successfully")

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        """
        Transcribe the audio bytes to text:
        1. Create a temp file on disk so that Parakeet can read it
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
            # Transcribe the audio file; result exposes full text
            result = self.model.transcribe(tmp_path)
            return str(result.text).strip()
        finally:
            # Clean up temp file after transcribing
            os.unlink(tmp_path)


# Shared ASR instance
_asr: ParakeetASR | None = None


def get_asr() -> ParakeetASR:
    """Return the shared ASR instance."""
    global _asr
    if _asr is None:
        # Create the ASR instance
        _asr = ParakeetASR()
    return _asr