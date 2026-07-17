"""Asset schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    filename: str
    name: str | None = None
    description: str | None = None
    content_type: str | None = None
    url: str | None = None
    created_at: datetime
