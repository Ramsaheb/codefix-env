from typing import Optional

from pydantic import BaseModel, Field


class ResetRequest(BaseModel):
    task: str = Field(
        default="easy",
        min_length=1,
        max_length=64,
        description="Task name: easy, medium, or hard",
    )
    session_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Existing session ID to reuse. If omitted, a new session is created.",
    )


class StepRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Session ID returned by /reset",
    )
    action: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Action or code-edit command to apply to current state",
    )