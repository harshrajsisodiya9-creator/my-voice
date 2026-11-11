# MyVoice — Harshraj's Voice Bot

> Talk to Harshraj's AI voice bot. Ask interview questions, hear spoken answers.

**Live URL:** https://myvoice-pi.vercel.app

## How to use

1. Open the link on your phone or laptop
2. Tap the **mic button** and ask a question
3. Hear Harshraj's answer spoken aloud
4. Or type a question in the text box

No installs, no sign-up, no API keys needed.

## Architecture

```
Browser (HTML/CSS/JS)
  │
  ├── MediaRecorder → audio blob (webm/mp4)
  │
  ├── POST /api/talk ──────────────────────► Vercel Python Serverless
  │     multipart: audio + history            │
  │                                           ├─ Groq Whisper STT
  │                                           │   (whisper-large-v3-turbo)
  │                                           │
  │                                           ├─ LangChain LCEL chain
  │                                           │   ChatGroq w/ 3-model fallback
  │                                           │   System prompt + persona.md
  │                                           │
  │                                           └─ Guardrails: rate limit,
  │                                               input caps, reply cleanup
  │
  ◄── JSON {transcript, reply} ◄──────────────┘
  │
  └── speechSynthesis → speaks reply aloud
```

## Design decisions

| Decision | Why |
|---|---|
| **No RAG / vector DB** | The persona fits in a single system prompt (~1000 tokens). A retrieval layer would add latency and complexity with zero benefit. |
| **Groq Whisper over browser STT** | `webkitSpeechRecognition` is Chrome-only and unreliable on mobile. Whisper via Groq gives consistent transcription across all browsers. |
| **3-model fallback chain** | Groq's free tier has tight per-model rate limits. Falling back across models (gpt-oss-120b → qwen3.8-27b → gpt-oss-20b) keeps the bot responsive. |
| **Browser speechSynthesis for TTS** | Free, zero-latency start, no API key. Prefers en-IN male voice. Sentences split individually to work around Chrome's utterance length limit. |
| **Stateless backend** | No database, no sessions. Conversation history is kept client-side (last 6 messages) and sent with each request. Simplifies deployment and eliminates state management. |
| **History sanitization** | Client-sent history is untrusted. Backend validates roles (only user/assistant), caps content length, and trims to 6 messages. Prevents prompt injection via history. |
| **LangChain LCEL (no LangGraph)** | The flow is linear: prompt → LLM → parse. LCEL handles this cleanly with `.with_fallbacks()` for model chaining. LangGraph would be unnecessary complexity. |

## Local setup

```bash
# Clone and enter directory
cd MyVoice

# Create .env from template
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# Install dependencies
pip install -r requirements.txt

# Run locally with Vercel CLI
npm i -g vercel
vercel dev
```

Open http://localhost:3000 in your browser.

## Deploy to Vercel

```bash
# Login (first time)
vercel login

# Deploy
vercel --prod

# Set the API key
vercel env add GROQ_API_KEY
# Paste your key when prompted, select all environments

# Redeploy to pick up the env var
vercel --prod
```

## Run tests

```bash
pip install pytest
pytest tests/ -v
```

## Project structure

```
api/index.py        → FastAPI routes (POST /api/talk, GET /api/health)
app/config.py       → All settings: env vars, model IDs, limits
app/speech.py       → Audio validation + Groq Whisper transcription
app/persona.py      → Persona loading, LLM chain with fallbacks, answer()
app/guardrails.py   → Rate limiting, input caps, history sanitization, reply cleanup
app/persona.md      → Persona facts (template — fill in your details)
public/             → Frontend: index.html, style.css, app.js
tests/              → pytest: guardrails, speech validation, persona (mocked)
```
