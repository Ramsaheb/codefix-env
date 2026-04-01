from env.state import CodeState

def get_task() -> CodeState:
    return CodeState(
        task_name="easy",
        code='print("Hello',
        error="SyntaxError: missing closing quote/parenthesis",
        target_hint='Convert to print("Hello")',
        max_steps=4,
    )