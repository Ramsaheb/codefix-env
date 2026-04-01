from typing import Tuple

from graders.testcases import get_testcases
from utils.code_executor import compile_code, execute_code


def grade_code(task_name: str, code: str) -> Tuple[float, str]:
    syntax_ok, syntax_error = compile_code(code)
    if not syntax_ok:
        return 0.0, syntax_error

    run_ok, namespace, run_error = execute_code(code)
    if not run_ok:
        return 0.3, run_error

    testcases = get_testcases(task_name)
    if not testcases:
        return 1.0, ""

    passed = 0
    failures = []

    for case in testcases:
        case_ok, fail_reason = _run_testcase(case, namespace, code)
        if case_ok:
            passed += 1
        else:
            failures.append(fail_reason)

    score = 0.3 + (0.7 * (passed / len(testcases)))
    return round(min(score, 1.0), 3), "; ".join(failures)


def _run_testcase(case: dict, namespace: dict, code: str) -> Tuple[bool, str]:
    kind = case.get("kind")

    if kind == "contains":
        required_text = case.get("text", "")
        ok = required_text in code
        return ok, f"Expected code to contain '{required_text}'"

    if kind == "call":
        fn_name = case.get("function")
        fn = namespace.get(fn_name)
        if not callable(fn):
            return False, f"Function '{fn_name}' not found"

        args = case.get("args", [])
        expected = case.get("expected")

        try:
            actual = fn(*args)
        except Exception as exc:
            return False, f"Function '{fn_name}' raised {exc.__class__.__name__}: {exc}"

        if actual != expected:
            return False, f"{fn_name}{tuple(args)} expected {expected}, got {actual}"

        return True, ""

    return False, "Unknown testcase kind"