from env.state import CodeState

def get_task() -> CodeState:
    return CodeState(
        task_name="hard",
        code="def compute(a, b):\n    if a > b\n        return a-b\n    return a-b",
        error="SyntaxError and logic issue",
        target_hint="Add missing colon and switch subtraction to addition",
        max_steps=6,
    )