"""Anthropic Claude provider. The only place the `anthropic` SDK is imported.

Business logic depends on the AIProvider interface, never on this module — swapping
providers is a config change (AI_DEFAULT_PROVIDER) plus a sibling class here.
"""
from __future__ import annotations

from app.ai.base import AIProvider, AIRequest, AIResponse


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str, default_model: str) -> None:
        import anthropic  # lazy: keep the dependency out of import paths that don't use it

        self._client = anthropic.Anthropic(api_key=api_key)
        self._default_model = default_model

    def generate(self, request: AIRequest) -> AIResponse:
        model = request.model or self._default_model
        kwargs: dict = {
            "model": model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system:
            kwargs["system"] = request.system

        resp = self._client.messages.create(**kwargs)
        text = "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
        return AIResponse(
            text=text,
            provider=self.name,
            model=model,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            raw={"stop_reason": resp.stop_reason},
        )
