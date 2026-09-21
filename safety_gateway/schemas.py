"""Strict Pydantic v2 request/response contracts for the safety gateway."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=False,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class PipelineDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class DetectedEntity(StrictModel):
    entity_type: str = Field(min_length=1)
    original: str = Field(min_length=1)
    token: str = Field(min_length=3, pattern=r"^<[A-Z][A-Z0-9_]*_[1-9]\d*>$")
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    score: float = Field(ge=0.0, le=1.0)

    @field_validator("end")
    @classmethod
    def end_after_start(cls, end: int, info: Any) -> int:
        start = info.data.get("start")
        if isinstance(start, int) and end <= start:
            raise ValueError("end must be greater than start")
        return end


class InboundRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=0, max_length=20_000)


class OutboundRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=0, max_length=40_000)


class SafetyProcessResult(StrictModel):
    session_id: str
    direction: Literal["inbound", "outbound"]
    original_text: str
    processed_text: str
    entities: list[DetectedEntity]
    steps_executed: list[str]
    blocked: bool = False
    block_category: str | None = None
    child_message: str | None = None
    had_image: bool = False
    faces_detected: int = Field(default=0, ge=0)


class ImageRedactRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=128)
    image_bytes: bytes = Field(min_length=1)

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=False,
        arbitrary_types_allowed=False,
    )


class ImageRedactResult(StrictModel):
    session_id: str
    content_type: Literal["image/png"]
    image_bytes: bytes
    byte_size: int = Field(gt=0)
