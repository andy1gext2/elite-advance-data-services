"""Heuristic sentiment + keyword analysis for reviews.

Deterministic and dependency-free so ingestion is fast and testable. This is the
same "heuristics now, learned model later" approach as the calendar's best-times:
the AI SENTIMENT module can replace `analyze_sentiment` without touching callers.
"""
from __future__ import annotations

import re
from collections import Counter

from app.models.enums import ReviewSentiment

POSITIVE_WORDS = {
    "love", "loved", "great", "excellent", "amazing", "awesome", "friendly",
    "fast", "clean", "best", "wonderful", "fantastic", "recommend", "delicious",
    "helpful", "perfect", "quick", "attentive", "welcoming", "fresh", "cozy",
    "professional", "outstanding", "brilliant", "happy", "enjoyed", "favorite",
}
NEGATIVE_WORDS = {
    "terrible", "awful", "slow", "rude", "dirty", "worst", "bad", "disappointing",
    "disappointed", "cold", "overpriced", "expensive", "waited", "wait", "never",
    "poor", "horrible", "unfriendly", "unprofessional", "mistake", "wrong",
    "cancelled", "canceled", "refund", "complaint", "avoid", "mediocre",
}

# Words too common to be useful as review "topics".
STOPWORDS = {
    "the", "and", "was", "were", "are", "this", "that", "with", "for", "have",
    "had", "has", "you", "your", "our", "their", "they", "them", "here", "there",
    "very", "just", "but", "not", "all", "get", "got", "out", "too", "will",
    "would", "could", "been", "when", "what", "which", "who", "how", "why",
    "from", "into", "than", "then", "some", "more", "most", "only", "also",
    "about", "over", "after", "before", "come", "came", "back", "went", "one",
    "place", "time", "really", "definitely", "again", "much", "such",
}

_WORD_RE = re.compile(r"[a-zA-Z']+")


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def analyze_sentiment(text: str, rating: int) -> str:
    """Blend the star rating with lexicon hits. Rating dominates; wording nudges."""
    words = set(_tokens(text))
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    score = (rating - 3) + (pos - neg)
    if score >= 1:
        return ReviewSentiment.POSITIVE.value
    if score <= -1:
        return ReviewSentiment.NEGATIVE.value
    return ReviewSentiment.NEUTRAL.value


def extract_keywords(text: str, limit: int = 8) -> list[str]:
    """Notable content words (>=4 chars, non-stopword), most frequent first."""
    counts = Counter(
        w for w in _tokens(text) if len(w) >= 4 and w not in STOPWORDS
    )
    return [w for w, _ in counts.most_common(limit)]


def needs_attention(rating: int, sentiment: str) -> bool:
    """Escalation recommendation: unhappy customer worth a prompt reply."""
    return rating <= 2 or sentiment == ReviewSentiment.NEGATIVE.value
