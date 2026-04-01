from tasks.easy import get_task as easy
from tasks.medium import get_task as medium
from tasks.hard import get_task as hard


TASK_FACTORIES = {
    "easy": easy,
    "medium": medium,
    "hard": hard,
}


def load_task(name: str):
    key = (name or "easy").lower()
    if key not in TASK_FACTORIES:
        available = ", ".join(sorted(TASK_FACTORIES.keys()))
        raise ValueError(f"Unknown task '{name}'. Available tasks: {available}")

    return TASK_FACTORIES[key]()