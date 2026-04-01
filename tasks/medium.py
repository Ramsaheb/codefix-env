from env.state import CodeState


def get_task() -> CodeState:
    return CodeState(
        task_name="medium",
        code="def add(a, b):\n    total = a - b\n    return total",
        error="LogicError: add uses subtraction when it should sum values",
        target_hint="Change subtraction assignment to addition",
        max_steps=5,
    )