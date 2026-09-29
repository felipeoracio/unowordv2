"""Provider boundary for personalized suggestions.

Phase 1 deliberately uses a deterministic provider. A future OpenAI-compatible
adapter can implement the same protocol without exposing credentials to Chrome
or changing route contracts.
"""

import os
import re
from typing import Protocol

from models.ai import AISuggestionResult


class SuggestionProvider(Protocol):
    name: str
    model: str

    async def generate_suggestion(self, context: str) -> AISuggestionResult: ...


class MockSuggestionProvider:
    name = "mock"

    def __init__(self, model: str) -> None:
        self.model = model

    async def generate_suggestion(self, context: str) -> AISuggestionResult:
        words = [w.lower() for w in re.findall(r"[\w'-]{4,}", context) if w.lower() not in {"that", "with", "from", "this", "your", "about"}]
        topics = list(dict.fromkeys(words))[:3]
        topic_text = ", ".join(topics) if topics else "your current thread"
        return AISuggestionResult(
            title="Follow the thread that still feels unfinished",
            suggestion=f"Write the next scene, reflection, or question connected to {topic_text}.",
            why="This is a local fallback suggestion. It uses only the context supplied to UnoWord and makes no claim about facts outside it.",
            related_topics=topics,
        )


def get_suggestion_provider() -> SuggestionProvider:
    provider = os.environ.get("AI_PROVIDER", "mock").lower()
    model = os.environ.get("AI_MODEL", "gpt-5.4-mini")
    if provider != "mock":
        # Fail closed rather than silently calling an unconfigured provider.
        raise RuntimeError(f"Unsupported AI_PROVIDER: {provider}")
    return MockSuggestionProvider(model)