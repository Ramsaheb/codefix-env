import sys
from typing import Any, Callable, Dict, Tuple


SAFE_BUILTINS = {
    "abs": abs,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "list": list,
    "len": len,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "str": str,
    "sum": sum,
    "tuple": tuple,
}

MAX_SOURCE_CHARS = 20_000
DEFAULT_MAX_EXECUTION_LINES = 4_000


class ExecutionLimitExceeded(RuntimeError):
    pass


def _run_with_line_limit(fn: Callable[[], Any], max_executed_lines: int) -> Any:
    counter = {"lines": 0}

    def tracer(frame, event, arg):  # noqa: ANN001
        if event == "line":
            counter["lines"] += 1
            if counter["lines"] > max_executed_lines:
                raise ExecutionLimitExceeded(
                    f"Execution limit exceeded ({max_executed_lines} lines)."
                )
        return tracer

    previous_tracer = sys.gettrace()
    sys.settrace(tracer)
    try:
        return fn()
    finally:
        sys.settrace(previous_tracer)


def compile_code(code: str) -> Tuple[bool, str]:
    if len(code) > MAX_SOURCE_CHARS:
        return False, f"Code exceeds max length of {MAX_SOURCE_CHARS} characters."

    try:
        compile(code, "<candidate>", "exec")
        return True, ""
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc.msg} (line {exc.lineno})"


def execute_code(code: str, max_executed_lines: int = DEFAULT_MAX_EXECUTION_LINES) -> Tuple[bool, Dict[str, Any], str]:
    syntax_ok, syntax_error = compile_code(code)
    if not syntax_ok:
        return False, {}, syntax_error

    namespace: Dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    try:
        _run_with_line_limit(
            lambda: exec(code, namespace, namespace),
            max_executed_lines=max_executed_lines,
        )
    except ExecutionLimitExceeded as exc:
        return False, {}, str(exc)
    except Exception as exc:
        return False, {}, f"{exc.__class__.__name__}: {exc}"

    return True, namespace, ""


def invoke_callable(
    fn: Callable[..., Any],
    *args: Any,
    max_executed_lines: int = DEFAULT_MAX_EXECUTION_LINES,
) -> Any:
    return _run_with_line_limit(
        lambda: fn(*args),
        max_executed_lines=max_executed_lines,
    )