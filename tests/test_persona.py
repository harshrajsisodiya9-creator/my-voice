from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from app.persona import answer


class TestAnswer:
    @patch("app.persona._get_chain")
    def test_returns_llm_reply(self, mock_chain):
        mock_chain.return_value.invoke.return_value = "I'm Harshraj and I love building things."
        result = answer("Tell me about yourself", [])
        assert result == "I'm Harshraj and I love building things."

    @patch("app.persona._get_chain")
    def test_passes_history(self, mock_chain):
        mock_chain.return_value.invoke.return_value = "Sure, as I mentioned..."
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        answer("Tell me more", history)
        call_args = mock_chain.return_value.invoke.call_args[0][0]
        assert len(call_args["history"]) == 2

    @patch("app.persona._get_chain")
    def test_fallback_on_all_models_down(self, mock_chain):
        mock_chain.return_value.invoke.side_effect = Exception("rate limited")
        result = answer("Hello", [])
        assert "overloaded" in result or "few seconds" in result

    def test_gemini_rate_limit_falls_back_to_groq(self):
        def fake_gemini(inputs):
            raise Exception("429 Resource exhausted")

        def fake_groq(inputs):
            return AIMessage(content="Fallback answer from Groq.")

        gemini = RunnableLambda(fake_gemini)
        groq = RunnableLambda(fake_groq)
        llm_with_fallback = gemini.with_fallbacks([groq])

        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a test bot.\n{persona}"),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ])
        chain = prompt | llm_with_fallback | StrOutputParser()

        import app.persona as persona_mod
        old_chain = persona_mod._chain
        persona_mod._chain = chain
        try:
            result = answer("Hello", [])
            assert "Fallback answer from Groq" in result
        finally:
            persona_mod._chain = old_chain
