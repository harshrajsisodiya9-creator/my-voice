from groq import Groq

from app.config import (
    ALLOWED_AUDIO_MIMES,
    GROQ_API_KEY,
    MAX_AUDIO_SIZE_BYTES,
    WHISPER_MODEL,
)


class AudioValidationError(Exception):
    pass


def validate_audio(data: bytes, content_type: str | None) -> str:
    """Validate audio size and mime type. Returns the file extension."""
    if not data:
        raise AudioValidationError("No audio data received. Please try recording again.")

    if len(data) > MAX_AUDIO_SIZE_BYTES:
        size_mb = MAX_AUDIO_SIZE_BYTES / (1024 * 1024)
        raise AudioValidationError(
            f"Audio file is too large. Please keep recordings under {size_mb:.0f} MB."
        )

    mime = (content_type or "").split(";")[0].strip().lower()
    ext = ALLOWED_AUDIO_MIMES.get(mime)
    if not ext:
        raise AudioValidationError(
            f"Unsupported audio format ({mime or 'unknown'}). "
            "Please use a modern browser that records in WebM or MP4."
        )
    return ext


def transcribe(data: bytes, content_type: str | None) -> str:
    """Validate audio and transcribe via Groq Whisper. Returns the transcript text."""
    ext = validate_audio(data, content_type)

    client = Groq(api_key=GROQ_API_KEY)
    transcription = client.audio.transcriptions.create(
        model=WHISPER_MODEL,
        file=(f"audio{ext}", data),
        response_format="text",
    )

    text = transcription.strip() if isinstance(transcription, str) else str(transcription).strip()
    if not text:
        raise AudioValidationError(
            "I couldn't hear anything in that recording. Could you try again, a bit louder?"
        )
    return text
