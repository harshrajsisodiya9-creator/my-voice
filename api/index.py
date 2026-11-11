import os
from pathlib import Path

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.guardrails import cap_input_text, check_rate_limit, clean_reply, sanitize_history
from app.persona import answer
from app.speech import AudioValidationError, transcribe

app = FastAPI()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/talk")
async def talk(
    request: Request,
    audio: UploadFile | None = File(None),
    text: str | None = Form(None),
    history: str | None = Form(None),
):
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip):
        return JSONResponse(
            status_code=429,
            content={
                "error": "You're asking questions faster than I can think! "
                "Give me a minute and try again."
            },
        )

    clean_history = sanitize_history(history)
    transcript = None

    if audio and audio.filename:
        try:
            data = await audio.read()
            transcript = transcribe(data, audio.content_type)
        except AudioValidationError as e:
            return JSONResponse(status_code=400, content={"error": str(e)})
        except Exception:
            return JSONResponse(
                status_code=500,
                content={"error": "Something went wrong processing your audio. Please try again."},
            )
        question = transcript
    elif text and text.strip():
        question = cap_input_text(text.strip())
    else:
        return JSONResponse(
            status_code=400,
            content={"error": "I didn't get a question. Try tapping the mic and speaking, or type something below."},
        )

    reply = answer(question, clean_history)
    reply = clean_reply(reply)

    return {"transcript": transcript, "reply": reply}


# Serve static files in local dev (must be AFTER API routes so they match first).
# Vercel serves public/ automatically in production.
_public = Path(__file__).resolve().parent.parent / "public"
if _public.is_dir() and not os.environ.get("VERCEL"):
    app.mount("/", StaticFiles(directory=str(_public), html=True), name="static")
