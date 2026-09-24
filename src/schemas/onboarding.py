"""
Onboarding-related Pydantic schemas.
"""

from typing import List

from pydantic import Field

from src.schemas.common import BaseSchema


class OnboardingStep(BaseSchema):
    """Single onboarding step status."""

    step: str
    name: str
    completed: bool
    current: bool = False


class OnboardingStatus(BaseSchema):
    """Response schema for onboarding status endpoint."""

    completed: bool
    current_step: int = Field(..., ge=1, le=3)
    steps: List[OnboardingStep]


class OnboardingCompleteResponse(BaseSchema):
    """Response schema for completing onboarding."""

    message: str = "Onboarding completed successfully"
    redirect_url: str = "/dashboard"
