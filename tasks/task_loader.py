from tasks.easy import get_task as easy
from tasks.medium import get_task as medium
from tasks.hard import get_task as hard
from tasks.expert import get_task as expert
from tasks.nightmare import get_task as nightmare
from env.state import CodeState


TASK_FACTORIES = {
    "easy": easy,
    "medium": medium,
    "hard": hard,
    "expert": expert,
    "nightmare": nightmare,
}


def load_task(name: str) -> CodeState:
    key = (name or "easy").lower()
    if key not in TASK_FACTORIES:
        available = ", ".join(sorted(TASK_FACTORIES.keys()))
        raise ValueError(f"Unknown task '{name}'. Available tasks: {available}")

    task_state = TASK_FACTORIES[key]()
    _validate_task_state(task_state, expected_name=key)
    return task_state


def available_tasks() -> list[str]:
    return sorted(TASK_FACTORIES.keys())


def _validate_task_state(task_state: CodeState, expected_name: str) -> None:
    if not isinstance(task_state, CodeState):
        raise ValueError("Task factory must return a CodeState instance.")

    if task_state.task_name != expected_name:
        raise ValueError(
            f"Task '{expected_name}' produced mismatched task_name '{task_state.task_name}'."
        )

    if not task_state.code.strip():
        raise ValueError(f"Task '{expected_name}' code must be non-empty.")

    if not task_state.error.strip():
        raise ValueError(f"Task '{expected_name}' error description must be non-empty.")

    if task_state.max_steps < 1 or task_state.max_steps > 64:
        raise ValueError(
            f"Task '{expected_name}' max_steps must be within [1, 64], got {task_state.max_steps}."
        )