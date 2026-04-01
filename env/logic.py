from env.actions import parse_action


def apply_action(code: str, raw_action: str) -> str:
    action, payload = parse_action(raw_action)

    if action == "noop":
        return code

    if action == "fix_syntax":
        return _fix_syntax(code)

    if action == "fix_logic":
        return _fix_logic(code)

    if action == "replace_line":
        return _replace_line(code, int(payload["line_no"]), str(payload["new_code"]))

    return code


def _fix_syntax(code: str) -> str:
    updated = code
    updated = updated.replace('print("Hello', 'print("Hello")')
    updated = updated.replace("if a > b\n", "if a > b:\n")
    updated = updated.replace("print(a-b", "print(a-b)")
    return updated


def _fix_logic(code: str) -> str:
    updated = code.replace("a - b", "a + b")
    updated = updated.replace("a-b", "a+b")
    return updated


def _replace_line(code: str, line_no: int, new_code: str) -> str:
    lines = code.splitlines()
    index = line_no - 1

    if index < 0 or index >= len(lines):
        return code

    lines[index] = new_code
    rebuilt = "\n".join(lines)

    if code.endswith("\n"):
        return rebuilt + "\n"

    return rebuilt