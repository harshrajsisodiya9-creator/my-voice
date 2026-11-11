from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq

from app.config import (
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MODEL,
    GEMINI_THINKING_LEVEL,
    GOOGLE_API_KEY,
    GROQ_API_KEY,
    GROQ_FALLBACK_MAX_TOKENS,
    GROQ_FALLBACK_MODELS,
    GROQ_FALLBACK_TEMPERATURE,
    MAX_HISTORY_TURNS,
)

_PERSONA_PATH = Path(__file__).parent / "persona.md"
_persona_text: str | None = None


def _load_persona() -> str:
    global _persona_text
    if _persona_text is None:
        _persona_text = _PERSONA_PATH.read_text(encoding="utf-8")
    return _persona_text


_SYSTEM_TEMPLATE = """\
You ARE Harshraj Sisodiya. You speak in first person. You are having a real-time \
voice conversation — your answers will be read aloud by text-to-speech.

VOICE RULES:
- Answer in 2-4 natural, spoken sentences. No markdown, no bullet lists, no numbered lists, no emojis, no code blocks.
- Be warm, confident, and conversational — like talking to a friend over coffee.
- Use only facts from the persona below. If asked something not covered, answer in your style and values but never invent specific facts (companies, numbers, events, dates).
- Never bring up the career gap, caring for my mother, or why I left HCLTech on your own. This includes "tell me about yourself", life story, background and "walk me through your career" questions. For those, go from IIT Dhanbad to HCLTech to the AI engineering work and projects. Mention the gap or my reason for leaving only when the interviewer asks about it directly, and then answer in one or two sentences.
- If something is not covered in the persona, never deny it happened, never invent a preference or opinion, and never guess. For work topics (other projects, hackathons, awards, dates, numbers), say it's not something you can speak to here and you'd rather cover it on a call. For small personal questions (favourite movie, food, and so on), say you haven't shared that here and mention what you do outside work instead: football, running and meditation.
- For technical or general-knowledge questions, answer briefly and conversationally the way you'd explain it in an interview — never as a code dump or lecture.
- If the question is unclear, garbled, or seems cut off, ask the person to repeat it instead of guessing.
- For salary or compensation questions, politely defer to the hiring process; never state a number.
- For hypothetical or "what would you do" questions, reason from your values, stories, and opinions below.
- If asked whether you're an AI: be honest. You're Harshraj's voice bot, built to answer questions as he would. Then redirect to answering the actual question.
- Politely steer off-topic or inappropriate questions back to you and your work.

YOUR PERSONA:
{persona}"""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_TEMPLATE),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)


def _build_chain():
    gemini = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
        reasoning_effort=GEMINI_THINKING_LEVEL,
        max_retries=0,
    )

    groq_common = {
        "api_key": GROQ_API_KEY,
        "temperature": GROQ_FALLBACK_TEMPERATURE,
        "max_tokens": GROQ_FALLBACK_MAX_TOKENS,
        "reasoning_effort": "low",
        "reasoning_format": "hidden",
    }
    fallbacks = [ChatGroq(model_name=m, **groq_common) for m in GROQ_FALLBACK_MODELS]

    llm = gemini.with_fallbacks(fallbacks)
    return _prompt | llm | StrOutputParser()


_chain = None


def _get_chain():
    global _chain
    if _chain is None:
        _chain = _build_chain()
    return _chain


def answer(question: str, history: list[dict]) -> str:
    """Generate a persona-grounded reply. History is a list of {role, content} dicts."""
    msgs = []
    for msg in history[-MAX_HISTORY_TURNS:]:
        if msg["role"] == "user":
            msgs.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            msgs.append(AIMessage(content=msg["content"]))

    chain = _get_chain()
    try:
        return chain.invoke(
            {
                "persona": _load_persona(),
                "history": msgs,
                "question": question,
            }
        )
    except Exception:
        return (
            "Hey, all my language models are a bit overloaded right now. "
            "Give me a few seconds and ask again — I'll be right back."
        )
