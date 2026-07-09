"""Content Calendar module — generates a single concise post idea per slot,
tailored to the channel and planning horizon."""
from __future__ import annotations

from dataclasses import replace

from app.ai.base import AIProvider, AIRequest, AIResponse
from app.models.enums import Channel


class CalendarModule:
    task_name = "calendar"

    def _system(self, biz: dict) -> str:
        parts = ["You are a marketing strategist planning a content calendar."]
        for label, key in (("Business", "name"), ("Industry", "industry"),
                           ("Target audience", "target_audience"), ("Tone", "tone")):
            if biz.get(key):
                parts.append(f"{label}: {biz[key]}")
        return "\n".join(parts)

    def run(self, request: AIRequest, provider: AIProvider) -> AIResponse:
        ctx = request.context or {}
        biz = ctx.get("business", {})
        channel = ctx.get("channel", Channel.GENERIC.value)
        timeframe = ctx.get("timeframe", "month")
        prompt = (
            f"Suggest ONE specific, on-brand {channel} post idea for a {timeframe} "
            f"content calendar. Theme/goal: {request.prompt.strip()}. "
            f"Return a single concise line (the idea only)."
        )
        return provider.generate(replace(request, system=self._system(biz), prompt=prompt, max_tokens=200))
