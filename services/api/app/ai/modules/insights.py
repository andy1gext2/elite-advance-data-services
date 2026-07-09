"""Business Insights module — the "AI business consultant".

Takes the RAG business context + a computed metrics snapshot (from the analytics
service) and returns a candid, plain-language assessment with recommendations.
The module never queries the DB; it reasons over the stats handed to it."""
from __future__ import annotations

from dataclasses import replace

from app.ai.base import AIProvider, AIRequest, AIResponse


def summarize_stats(stats: dict) -> str:
    """Flatten the metrics snapshot into a compact line the model can reason over."""
    k = stats.get("kpis", {})
    parts = [
        f"content pieces: {k.get('total_content', 0)}",
        f"published posts: {k.get('published_posts', 0)}",
        f"pending schedules: {k.get('pending_schedules', 0)}",
        f"reviews: {k.get('total_reviews', 0)}",
        f"average rating: {k.get('average_rating', 0)}",
        f"response rate: {round(k.get('response_rate', 0) * 100)}%",
        f"reviews needing attention: {k.get('needs_attention', 0)}",
    ]
    return "; ".join(parts)


class BusinessInsightsModule:
    task_name = "business_insights"

    def _system(self, biz: dict) -> str:
        parts = [
            "You are a candid, practical business consultant reviewing a small "
            "business's marketing and reputation dashboard.",
            "Give a short, honest assessment in plain language, then concrete next steps.",
            "Only use the numbers provided — never invent metrics.",
        ]
        for label, key in (("Business", "name"), ("Industry", "industry"), ("Goals", "goals")):
            if biz.get(key):
                parts.append(f"{label}: {biz[key]}")
        return "\n".join(parts)

    def run(self, request: AIRequest, provider: AIProvider) -> AIResponse:
        ctx = request.context or {}
        biz = ctx.get("business", {})
        stats = ctx.get("stats", {})
        prompt = (
            "Here are this month's marketing metrics:\n"
            f"{summarize_stats(stats)}\n\n"
            "Answer the owner's question: \"How is my business doing?\" "
            "Give a 2-3 sentence assessment, then 3 specific, prioritized recommendations."
        )
        return provider.generate(
            replace(request, system=self._system(biz), prompt=prompt, max_tokens=600)
        )
