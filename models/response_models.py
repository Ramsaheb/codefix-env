from typing import Any, Dict, List, Optional

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


class SchemaResponse(BaseModel):
    action: Dict[str, Any]
    observation: Dict[str, Any]
    state: Dict[str, Any]


class MetadataResponse(BaseModel):
    name: str
    description: str
    version: str
    author: str
    documentation_url: str
    readme_content: Optional[str] = None
    tasks: List[str]
