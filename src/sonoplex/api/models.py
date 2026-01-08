"""Pydantic request/response models for Sonoplex API."""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class VirtualDeviceCreatePayload(BaseModel):
    """Payload for creating a new virtual device."""
    name: str = Field(..., min_length=1)
    member_uuids: List[str] = Field(..., min_items=1)


class VirtualDeviceUpdatePayload(BaseModel):
    """Payload for updating an existing virtual device."""
    name: Optional[str] = Field(default=None, min_length=1)
    member_uuids: Optional[List[str]] = Field(default=None, min_items=1)


class OnboardingStateUpdate(BaseModel):
    """Payload for updating onboarding wizard state."""
    completed: Optional[bool] = None
    steps: Optional[Dict[str, Any]] = Field(default=None)


class AudioSettingsUpdate(BaseModel):
    """Payload for updating device audio settings."""
    bitrate_kbps: Optional[int] = Field(default=None, ge=0, le=10000)
    sample_rate_hz: Optional[int] = Field(default=None, ge=0, le=384000)
