"""Domain enums. Stored as strings (portable) and validated in the app layer."""
from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

    @property
    def rank(self) -> int:
        order = {"owner": 3, "admin": 2, "editor": 1, "viewer": 0}
        return order[self.value]

    def at_least(self, other: "Role") -> bool:
        return self.rank >= other.rank


class PlanTier(str, Enum):
    STARTER = "starter"
    PROFESSIONAL = "professional"
    GROWTH = "growth"
    ENTERPRISE = "enterprise"


class Channel(str, Enum):
    """Where a piece of content is destined for."""
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    X = "x"
    THREADS = "threads"
    GOOGLE_BUSINESS = "google_business"
    BLOG = "blog"
    EMAIL = "email"
    SMS = "sms"
    VIDEO = "video"
    GENERIC = "generic"


class ContentType(str, Enum):
    SOCIAL_POST = "social_post"
    BLOG_ARTICLE = "blog_article"
    EMAIL = "email"
    SMS = "sms"
    VIDEO_SCRIPT = "video_script"
    CAPTIONS = "captions"
    HASHTAGS = "hashtags"
    CTA = "cta"


class ContentStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class Platform(str, Enum):
    """Connectable social/publishing platforms (subset of Channel with real accounts)."""
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    X = "x"
    THREADS = "threads"
    GOOGLE_BUSINESS = "google_business"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"


class ReviewSentiment(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class ReviewStatus(str, Enum):
    NEW = "new"            # ingested, not yet responded to
    RESPONDED = "responded"


class ScheduleStatus(str, Enum):
    PENDING = "pending"        # queued, waiting for its scheduled time
    PUBLISHING = "publishing"  # picked up by the publish engine
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELED = "canceled"


UNLIMITED = -1  # sentinel for plan limits
