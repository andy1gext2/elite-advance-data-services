"""Content Generation module.

Owns prompt construction for platform-tailored content. Reads RAG-retrieved
business context + the target (channel, content_type) from the request context,
builds a system + user prompt, and delegates to the provider. The module is the
only place that knows how to write for a given platform.
"""
from __future__ import annotations

from dataclasses import replace

from app.ai.base import AIProvider, AIRequest, AIResponse
from app.models.enums import Channel, ContentType

# Per-content-type generation ceilings (keeps social short, blogs long).
MAX_TOKENS: dict[str, int] = {
    ContentType.SOCIAL_POST.value: 800,
    ContentType.BLOG_ARTICLE.value: 4000,
    ContentType.EMAIL.value: 1500,
    ContentType.SMS.value: 300,
    ContentType.VIDEO_SCRIPT.value: 1500,
    ContentType.CAPTIONS.value: 600,
    ContentType.HASHTAGS.value: 400,
    ContentType.CTA.value: 400,
}

# Platform-specific writing guidance (voice/length/format).
CHANNEL_GUIDE: dict[str, str] = {
    Channel.INSTAGRAM.value: "Instagram: punchy, visual, warm; 3-6 relevant hashtags; 1-2 emoji max.",
    Channel.FACEBOOK.value: "Facebook: conversational and community-oriented; a clear call to action.",
    Channel.LINKEDIN.value: "LinkedIn: professional, insight-led, no hype; minimal hashtags.",
    Channel.X.value: "X/Twitter: under 280 characters, sharp hook, at most 1-2 hashtags.",
    Channel.THREADS.value: "Threads: casual and authentic; conversational opener.",
    Channel.GOOGLE_BUSINESS.value: "Google Business Profile: concise, informative, locally relevant; clear CTA.",
    Channel.BLOG.value: "Blog: SEO-aware article with a title, intro, scannable sections, and a conclusion.",
    Channel.EMAIL.value: "Email: subject line + short body with one primary CTA.",
    Channel.SMS.value: "SMS: under 160 characters, direct, one CTA, no links unless essential.",
    Channel.VIDEO.value: "Short video script: hook in the first 3 seconds, then beats, then CTA.",
    Channel.GENERIC.value: "General marketing copy.",
}

CONTENT_TYPE_GUIDE: dict[str, str] = {
    ContentType.CAPTIONS.value: "Produce 3 distinct caption variations.",
    ContentType.HASHTAGS.value: "Produce 10-15 relevant, non-spammy hashtags.",
    ContentType.CTA.value: "Produce 3 call-to-action variants of increasing urgency.",
}


class ContentModule:
    task_name = "content"

    def _system(self, biz: dict, examples: list[str] | None = None) -> str:
        parts = [
            "You are an expert marketing manager writing on behalf of a business.",
            "Write professional, on-brand marketing content optimized for the target platform.",
            "Never invent facts about the business beyond the context provided.",
        ]
        for label, key in (
            ("Business", "name"),
            ("Industry", "industry"),
            ("Target audience", "target_audience"),
            ("Brand voice", "brand_voice"),
            ("Tone", "tone"),
            ("Goals", "goals"),
            ("Website", "website"),
            ("Description", "description"),
        ):
            val = biz.get(key)
            if val:
                parts.append(f"{label}: {val}")
        if examples:
            parts.append(
                "\nThe business owner has APPROVED these past posts. Learn their voice, "
                "rhythm, structure, and personality, and make new content feel consistent "
                "with them — echo the style, never copy any of them verbatim:"
            )
            for i, ex in enumerate(examples, 1):
                parts.append(f"[Approved example {i}]\n{ex}")
        return "\n".join(parts)

    def _user_prompt(self, channel: str, content_type: str, brief: str) -> str:
        guide = CHANNEL_GUIDE.get(channel, CHANNEL_GUIDE[Channel.GENERIC.value])
        extra = CONTENT_TYPE_GUIDE.get(content_type, "")
        lines = [
            f"Create a {content_type.replace('_', ' ')} for {channel}.",
            guide,
        ]
        if extra:
            lines.append(extra)
        lines.append(f"\nMarketing brief / idea:\n{brief.strip()}")
        lines.append("\nReturn only the finished content, ready to post.")
        return "\n".join(lines)

    def run(self, request: AIRequest, provider: AIProvider) -> AIResponse:
        ctx = request.context or {}
        biz = ctx.get("business", {})
        channel = ctx.get("channel", Channel.GENERIC.value)
        content_type = ctx.get("content_type", ContentType.SOCIAL_POST.value)
        examples = ctx.get("approved_examples") or []

        refined = replace(
            request,
            system=self._system(biz, examples),
            prompt=self._user_prompt(channel, content_type, request.prompt),
            max_tokens=MAX_TOKENS.get(content_type, request.max_tokens),
        )
        return provider.generate(refined)
