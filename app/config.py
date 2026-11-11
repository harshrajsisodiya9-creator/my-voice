import os

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# Primary LLM — Gemini
GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_THINKING_LEVEL = "minimal"
GEMINI_MAX_OUTPUT_TOKENS = 400

# Fallback LLM models (Groq) — used when Gemini is rate-limited
GROQ_FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
]
GROQ_FALLBACK_TEMPERATURE = 0.6
GROQ_FALLBACK_MAX_TOKENS = 250

# Whisper STT
WHISPER_MODEL = "whisper-large-v3-turbo"

# Audio constraints
MAX_AUDIO_SIZE_BYTES = 4 * 1024 * 1024  # 4 MB (under Vercel's 4.5 MB body limit)
MAX_AUDIO_DURATION_SEC = 30
ALLOWED_AUDIO_MIMES = {
    "audio/webm": ".webm",
    "audio/mp4": ".mp4",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "audio/x-m4a": ".m4a",
    "audio/mp4a-latm": ".m4a",
}

# Text input constraints
MAX_TEXT_LENGTH = 500
MAX_HISTORY_CONTENT_LENGTH = 1000

# Conversation history
MAX_HISTORY_TURNS = 6

# Rate limiting (best-effort, in-memory, per serverless instance)
RATE_LIMIT_REQUESTS = 20
RATE_LIMIT_WINDOW_SEC = 60

# Reply cleanup
MAX_REPLY_LENGTH = 600
