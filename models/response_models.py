from typing import List

from pydantic import BaseModel


class Observation(BaseModel):
    task: str
    code: str
    error: str
    step_count: int
    history: List[str]
    score: float


class ResetResponse(BaseModel):
    state: Observation


class StepResponse(BaseModel):
    state: Observation
    reward: float
    done: bool
    score: float