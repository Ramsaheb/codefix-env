from pydantic import BaseModel, Field


class ResetRequest(BaseModel):
    task: str = Field(default="easy", description="Task name: easy, medium, or hard")


class StepRequest(BaseModel):
    action: str = Field(..., description="Action to apply to current code state")