from env.state import CodeState


def get_task() -> CodeState:
    return CodeState(
        task_name="nightmare",
        code=(
            "def synthesize(a, b, c):\n"
            "    if a > b\n"
            "        return a-b+c\n"
            "    return b-a+c"
        ),
        error="SyntaxError plus branch-wise logic bug",
        target_hint="Add missing colon and convert both subtraction branches into additive composition",
        max_steps=8,
    )