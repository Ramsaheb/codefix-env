"""
OpenEnv-compliant typed models for CodeFixEnv.

CodeFixAction, CodeFixObservation, and CodeFixState extend the OpenEnv
base classes (Action, Observation, State) so the framework can
serialise/deserialise them automatically.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from openenv.core.env_server.types import Action, Observation, State


class CodeFixAction(Action):
    """A single debugging action submitted by the agent."""

    action: str = ""


class CodeFixObservation(Observation):
    """
    Observation returned after reset() or step().

    Inherits from Observation which provides:
      - done: bool
      - reward: float | None
      - metadata: Dict[str, Any]
    """

    task: str = ""
    code: str = ""
    error: str = ""
    step_count: int = 0
    history: List[str] = Field(default_factory=list)
    score: float = 0.0


class CodeFixReward(BaseModel):
    """Typed reward details for a single transition."""

    value: float = 0.0
    previous_score: float = 0.0
    current_score: float = 0.0
    delta: float = 0.0
    changed_lines: int = 0
    action_error: str = ""
    grade_error: str = ""


class CodeFixState(State):
    """
    Internal environment state.

    Inherits from State which provides:
      - episode_id: Optional[str]
      - step_count: int
    """

    task_name: str = ""
    code: str = ""
    error: str = ""
    max_steps: int = 6
    target_hint: str = ""
    last_score: float = 0.0
    history: List[str] = Field(default_factory=list)
