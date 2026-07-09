"""AI orchestration entrypoint.

Flow (see docs/architecture.md):
    User Request -> AIRouter.classify -> specialized module -> provider -> AIResponse

This is a skeleton: `classify` uses simple heuristics for now and will grow into a
proper classifier. Specialized modules live in app/ai/modules/ and are registered here.
"""
from __future__ import annotations

from app.ai.base import AIProvider, AIRequest, AIResponse, TaskType
from app.ai.modules.calendar import CalendarModule
from app.ai.modules.content import ContentModule
from app.ai.modules.insights import BusinessInsightsModule
from app.ai.modules.review import ReviewResponseModule


class AIRouter:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider
        # Specialized modules per task. More land here as phases ship
        # (strategy, sentiment, ...).
        self._modules = {
            TaskType.CONTENT: ContentModule(),
            TaskType.CALENDAR: CalendarModule(),
            TaskType.REVIEW_RESPONSE: ReviewResponseModule(),
            TaskType.BUSINESS_INSIGHTS: BusinessInsightsModule(),
        }

    def classify(self, prompt: str) -> TaskType:
        """Map a raw request to a task type. Placeholder heuristics — replace with a
        proper (possibly model-based) classifier in Phase 2."""
        p = prompt.lower()
        if any(k in p for k in ("review", "respond to")):
            return TaskType.REVIEW_RESPONSE
        if any(k in p for k in ("sentiment", "feel about")):
            return TaskType.SENTIMENT
        if any(k in p for k in ("how is my business", "insight", "how am i doing")):
            return TaskType.BUSINESS_INSIGHTS
        if any(k in p for k in ("campaign", "promotion")):
            return TaskType.CAMPAIGN
        if any(k in p for k in ("seo", "blog", "keyword")):
            return TaskType.SEO
        return TaskType.CONTENT

    def handle(self, request: AIRequest) -> AIResponse:
        """Dispatch to the specialized module for the request's task.

        Tasks without a dedicated module yet pass straight through to the provider.
        """
        module = self._modules.get(request.task)
        if module is not None:
            return module.run(request, self._provider)
        return self._provider.generate(request)
