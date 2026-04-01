from env.state import CodeState

def get_task() -> CodeState:
    return CodeState(
        task_name="medium",
        code="def add(a, b):\n    return a - b",
        error="LogicError: add uses subtraction instead of addition",
        target_hint="Change subtraction to addition",
        max_steps=5,
    )