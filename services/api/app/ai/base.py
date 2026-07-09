"""Provider-agnostic AI contracts.

Every AI provider (Anthropic, OpenAI, ...) implements `AIProvider`. Business logic
and AI modules depend ONLY on these types — never on a vendor SDK directly. Swapping
providers is a config change plus one class, with zero changes to modules.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class TaskType(str, Enum):
    """What the AI Router classifies an incoming request into -> specialized module."""
    CONTENT = "content"
    CALENDAR = "calendar"
    MARKETING_STRATEGY = "marketing_strategy"
    REVIEW_RESPONSE = "review_response"
    SENTIMENT = "sentiment"
    BUSINESS_INSIGHTS = "business_insights"
    ANALYTICS_SUMMARY = "analytics_summary"
    CAMPAIGN = "campaign"
    SEO = "seo"


@dataclass
class AIRequest:
    """A single unit of work handed to a provider.

    `context` carries RAG-retrieved business data (profile, brand voice, products,
    history) — the AI must never rely on memory across requests.
    """
    task: TaskType
    prompt: str
    business_id: str
    context: dict = field(default_factory=dict)
    system: str | None = None
    max_tokens: int = 1024
    temperature: float = 0.7
    model: str | None = None  # provider default if None


@dataclass
class AIResponse:
    text: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict = field(default_factory=dict)


class AIProvider(ABC):
    """Interface every provider implements."""

    name: str = "base"

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:  # pragma: no cover - interface
        ...
