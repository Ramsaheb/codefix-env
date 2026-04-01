from tasks.easy import get_task as easy
from tasks.medium import get_task as medium
from tasks.hard import get_task as hard
from tasks.expert import get_task as expert
from tasks.nightmare import get_task as nightmare


TASK_FACTORIES = {
    "easy": easy,
    "medium": medium,
    "hard": hard,
    "expert": expert,
    "nightmare": nightmare,
}


def load_task(name: str):
    key = (name or "easy").lower()
    if key not in TASK_FACTORIES:
        available = ", ".join(sorted(TASK_FACTORIES.keys()))
        raise ValueError(f"Unknown task '{name}'. Available tasks: {available}")

    return TASK_FACTORIES[key]()


def available_tasks() -> list[str]:
    return sorted(TASK_FACTORIES.keys())