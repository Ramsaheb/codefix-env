from dataclasses import dataclass, field
from typing import Any, Dict, List


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
            "score": self.last_score,
        }