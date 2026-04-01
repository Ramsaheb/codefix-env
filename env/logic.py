import re

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

    if action == "append_line":
        return _append_line(code, str(payload["new_code"]))

    if action == "delete_line":
        return _delete_line(code, int(payload["line_no"]))

    if action == "replace_text":
        return _replace_text(code, str(payload["old_text"]), str(payload["new_text"]))

    return code


def _fix_syntax(code: str) -> str:
    updated = code
    updated = updated.replace('print("Hello', 'print("Hello")')

    # Add a missing colon for simple if/elif/else/for/while/def/class statements.
    updated = re.sub(
        r"(?m)^(\s*(?:if|elif|else|for|while|def|class)\b[^:\n]*)$",
        r"\1:",
        updated,
    )

    updated = updated.replace("print(a-b", "print(a-b)")
    updated = updated.replace("print(a+b", "print(a+b)")
    return updated


def _fix_logic(code: str) -> str:
    updated = code

    replacements = {
        "a - b": "a + b",
        "a-b": "a+b",
        "b - a": "a + b",
        "b-a": "a+b",
        "return total - 1": "return total + 1",
    }
    for source, target in replacements.items():
        updated = updated.replace(source, target)

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


def _append_line(code: str, new_code: str) -> str:
    suffix = "\n" if code and not code.endswith("\n") else ""
    return f"{code}{suffix}{new_code}\n"


def _delete_line(code: str, line_no: int) -> str:
    lines = code.splitlines()
    index = line_no - 1
    if index < 0 or index >= len(lines):
        return code

    del lines[index]
    rebuilt = "\n".join(lines)
    if code.endswith("\n") and rebuilt:
        return rebuilt + "\n"
    return rebuilt


def _replace_text(code: str, old_text: str, new_text: str) -> str:
    return code.replace(old_text, new_text)