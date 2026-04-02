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
    session_id: str
    state: Observation


class StateResponse(BaseModel):
    session_id: str
    state: Observation


class StepResponse(BaseModel):
    session_id: str
    state: Observation
    reward: float
    done: bool
    score: float