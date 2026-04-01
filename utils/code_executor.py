from typing import Any, Dict, Tuple


SAFE_BUILTINS = {
    "abs": abs,
    "len": len,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "sum": sum,
}


def compile_code(code: str) -> Tuple[bool, str]:
    try:
        compile(code, "<candidate>", "exec")
        return True, ""
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc.msg} (line {exc.lineno})"


def execute_code(code: str) -> Tuple[bool, Dict[str, Any], str]:
    syntax_ok, syntax_error = compile_code(code)
    if not syntax_ok:
        return False, {}, syntax_error

    namespace: Dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    try:
        exec(code, namespace, namespace)
    except Exception as exc:
        return False, {}, f"{exc.__class__.__name__}: {exc}"

    return True, namespace, ""