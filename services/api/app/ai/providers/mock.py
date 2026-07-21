"""Deterministic provider for dev/tests — no API key, no network.

Produces plausible, business-aware text so the whole pipeline (RAG → module →
persistence → API) is testable without spending tokens.
"""
from __future__ import annotations

from app.ai.base import AIProvider, AIRequest, AIResponse, TaskType


class MockProvider(AIProvider):
    name = "mock"

    def __init__(self, model: str = "mock-model") -> None:
        self._model = model

    def generate(self, request: AIRequest) -> AIResponse:
        ctx = request.context or {}
        biz = ctx.get("business", {})
        name = biz.get("name", "the business")
        tone = biz.get("tone") or "friendly"

        if request.task == TaskType.REVIEW_RESPONSE:
            text = self._review_reply(ctx, name)
        elif request.task == TaskType.INDUSTRY_TRENDS:
            text = self._industry_trends(ctx)
        elif request.task == TaskType.BUSINESS_INSIGHTS:
            text = self._insights(ctx, name)
        else:
            channel = ctx.get("channel", "generic")
            ctype = ctx.get("content_type", "social_post")
            text = (
                f"[{channel}/{ctype}] {name} ({tone} tone): {request.prompt.strip()} "
                f"— crafted for {channel}."
            )
        model = request.model or self._model
        return AIResponse(
            text=text,
            provider=self.name,
            model=model,
            input_tokens=max(1, len(request.prompt) // 4),
            output_tokens=max(1, len(text) // 4),
            raw={"mock": True},
        )

    def _industry_trends(self, ctx: dict) -> str:
        """Deterministic JSON trend brief so the industry-trends flow is testable
        without a real model. Mirrors the structured schema the real prompt asks for."""
        import json

        industry = ctx.get("industry", "your industry")
        month = ctx.get("month", "this month")
        return json.dumps({
            "keywords": [f"{industry} tips", f"local {industry}", "small business", "behind the scenes"],
            "products": [f"signature {industry} item", "seasonal special", "gift bundle"],
            "services": [f"{industry} consultation", "loyalty program", "same-day service"],
            "seasonal": [f"{month} promotion", f"{month} seasonal favorite"],
            "post_ideas": [
                {"title": f"Show a behind-the-scenes look at your {industry}", "why": f"Builds trust and personality for a {industry} audience.", "channel": "instagram"},
                {"title": f"Highlight your top {month} seasonal offer", "why": "Seasonal relevance drives timely engagement.", "channel": "facebook"},
                {"title": "Share a quick customer win or testimonial", "why": "Social proof converts nearby prospects.", "channel": "google_business"},
            ],
        })

    def _review_reply(self, ctx: dict, name: str) -> str:
        """A plausible, sentiment-appropriate reply so the reputation flow is
        testable without a real model."""
        rating = ctx.get("rating", 3)
        author = ctx.get("author_name") or "there"
        if rating >= 4:
            return (
                f"Hi {author}, thank you so much for the kind words — the whole "
                f"team at {name} really appreciates it. We hope to see you again soon!"
            )
        if rating <= 2:
            return (
                f"Hi {author}, we're truly sorry your experience with {name} fell "
                f"short. This isn't the standard we hold ourselves to — please reach "
                f"out so we can make it right."
            )
        return (
            f"Hi {author}, thank you for the honest feedback. We're always working "
            f"to improve at {name}, and we'd love another chance to impress you."
        )

    def _insights(self, ctx: dict, name: str) -> str:
        """A plausible consultant-style assessment grounded in the passed stats."""
        k = (ctx.get("stats") or {}).get("kpis", {})
        rating = k.get("average_rating", 0)
        reviews = k.get("total_reviews", 0)
        content = k.get("total_content", 0)
        attention = k.get("needs_attention", 0)
        return (
            f"Overall, {name} is building solid momentum: you've produced {content} "
            f"pieces of content and hold a {rating}-star average across {reviews} reviews. "
            f"Reputation is your strongest asset, but there is room to publish more "
            f"consistently.\n\n"
            f"Recommendations:\n"
            f"1. Respond to the {attention} review(s) flagged for attention this week.\n"
            f"2. Schedule your approved content so posting stays consistent.\n"
            f"3. Turn your best 5-star reviews into testimonial posts to compound trust."
        )
