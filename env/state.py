from dataclasses import dataclass, field
from typing import Any, Dict, List


PUBLIC_SCORE_EPSILON = 0.001


def to_public_score(score: float) -> float:
    bounded = min(max(float(score), PUBLIC_SCORE_EPSILON), 1.0 - PUBLIC_SCORE_EPSILON)
    return round(bounded, 3)


@dataclass
class CodeState:
    task_name: str
    code: str
    error: str
    step_count: int = 0
    history: List[str] = field(default_factory=list)
    max_steps: int = 6
    target_hint: str = ""
    last_score: float = 0.0

    def to_observation(self) -> Dict[str, Any]:
        return {
            "task": self.task_name,
            "code": self.code,
            "error": self.error,
            "step_count": self.step_count,
            "history": list(self.history),
            "score": to_public_score(self.last_score),
        }