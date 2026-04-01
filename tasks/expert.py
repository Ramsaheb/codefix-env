from env.state import CodeState


def get_task() -> CodeState:
    return CodeState(
        task_name="expert",
        code=(
            "def stabilize(a, b):\n"
            "    result = a - b\n"
            "    if result < 0:\n"
            "        return 0\n"
            "    if result > 100:\n"
            "        return 100\n"
            "    return result"
        ),
        error="LogicError: stabilize subtracts values instead of combining them",
        target_hint="Use addition before boundary clamps",
        max_steps=7,
    )