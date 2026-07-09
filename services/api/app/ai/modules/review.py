"""Review Response module — drafts an on-brand reply to a customer review.

Reads RAG business context + the review (rating, body, sentiment) from the request
context, and shapes the reply: grateful for praise, empathetic and solution-oriented
for criticism. The module is the only place that knows how to answer a review."""
from __future__ import annotations

from dataclasses import replace

from app.ai.base import AIProvider, AIRequest, AIResponse
from app.models.enums import ReviewSentiment


class ReviewResponseModule:
    task_name = "review_response"

    def _system(self, biz: dict) -> str:
        parts = [
            "You are the owner's reputation manager replying to a customer review.",
            "Write a concise, sincere, professional public reply.",
            "Thank happy customers warmly; for unhappy ones, apologize, take "
            "responsibility, and offer to make it right — never defensive, never generic.",
            "Do not invent facts beyond the business context provided.",
        ]
        for label, key in (("Business", "name"), ("Industry", "industry"), ("Tone", "tone")):
            if biz.get(key):
                parts.append(f"{label}: {biz[key]}")
        return "\n".join(parts)

    def run(self, request: AIRequest, provider: AIProvider) -> AIResponse:
        ctx = request.context or {}
        biz = ctx.get("business", {})
        rating = ctx.get("rating", 3)
        sentiment = ctx.get("sentiment", ReviewSentiment.NEUTRAL.value)
        author = ctx.get("author_name") or "the customer"

        prompt = (
            f"Write a public reply to this {rating}-star ({sentiment}) review "
            f"from {author}:\n\n\"{request.prompt.strip()}\"\n\n"
            f"Return only the reply text, ready to post."
        )
        return provider.generate(
            replace(request, system=self._system(biz), prompt=prompt, max_tokens=400)
        )
