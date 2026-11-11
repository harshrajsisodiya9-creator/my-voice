import pytest

from app.speech import AudioValidationError, validate_audio


class TestValidateAudio:
    def test_empty_data_raises(self):
        with pytest.raises(AudioValidationError, match="No audio data"):
            validate_audio(b"", "audio/webm")

    def test_oversized_raises(self):
        big = b"x" * (4 * 1024 * 1024 + 1)
        with pytest.raises(AudioValidationError, match="too large"):
            validate_audio(big, "audio/webm")

    def test_bad_mime_raises(self):
        with pytest.raises(AudioValidationError, match="Unsupported audio format"):
            validate_audio(b"data", "video/mp4")

    def test_none_mime_raises(self):
        with pytest.raises(AudioValidationError, match="Unsupported audio format"):
            validate_audio(b"data", None)

    def test_webm_returns_ext(self):
        assert validate_audio(b"data", "audio/webm") == ".webm"

    def test_mp4_returns_ext(self):
        assert validate_audio(b"data", "audio/mp4") == ".mp4"

    def test_wav_returns_ext(self):
        assert validate_audio(b"data", "audio/wav") == ".wav"

    def test_mime_with_params(self):
        assert validate_audio(b"data", "audio/webm; codecs=opus") == ".webm"

    def test_exact_size_limit_passes(self):
        data = b"x" * (4 * 1024 * 1024)
        assert validate_audio(data, "audio/webm") == ".webm"
