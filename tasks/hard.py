from env.state import CodeState


def get_task() -> CodeState:
    return CodeState(
        task_name="hard",
        code="def compute(a, b):\n    if a > b\n        return a-b\n    return b-a",
        error="SyntaxError and branch-specific logic issues",
        target_hint="Add missing colon and make both branches perform addition",
        max_steps=6,
    )