import sys
from typing import Any, Callable, Dict, Tuple


SAFE_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "list": list,
    "len": len,
    "map": map,
    "max": max,
    "min": min,
    "pow": pow,
    "print": print,
    "range": range,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}

MAX_SOURCE_CHARS = 20_000
DEFAULT_MAX_EXECUTION_LINES = 4_000
MAX_RECURSION_LIMIT = 1_000


class ExecutionLimitExceeded(RuntimeError):
    pass


def _run_with_line_limit(fn: Callable[[], Any], max_executed_lines: int) -> Any:
    if max_executed_lines < 1:
        raise ValueError("max_executed_lines must be >= 1")

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
    if not isinstance(code, str):
        return False, "Code must be a string."

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

    if max_executed_lines < 1:
        return False, {}, "max_executed_lines must be >= 1"

    namespace: Dict[str, Any] = {"__builtins__": SAFE_BUILTINS}
    previous_recursion_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(MAX_RECURSION_LIMIT)
        _run_with_line_limit(
            lambda: exec(code, namespace, namespace),
            max_executed_lines=max_executed_lines,
        )
    except ExecutionLimitExceeded as exc:
        return False, {}, str(exc)
    except Exception as exc:
        return False, {}, f"{exc.__class__.__name__}: {exc}"
    finally:
        sys.setrecursionlimit(previous_recursion_limit)

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