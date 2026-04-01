from typing import Tuple

from graders.testcases import get_testcases
from utils.code_executor import (
    ExecutionLimitExceeded,
    compile_code,
    execute_code,
    invoke_callable,
)


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
    score = round(min(score, 1.0), 3)

    anti_cheat_error = _detect_hardcoded_solution(code, testcases)
    if anti_cheat_error:
        score = min(score, 0.2)
        failures.append(anti_cheat_error)

    return score, "; ".join(failures)


def _detect_hardcoded_solution(code: str, testcases: list[dict]) -> str:
    call_cases = [case for case in testcases if case.get("kind") == "call"]
    if len(call_cases) < 2:
        return ""

    compact_code = "".join(code.split())
    suspicious_hits = 0

    for case in call_cases:
        args = case.get("args", [])
        if not isinstance(args, list) or not args:
            continue

        tuple_literal = "(" + ",".join(_compact_literal(arg) for arg in args) + ")"
        if f"=={tuple_literal}" in compact_code:
            suspicious_hits += 1

        and_compare_pattern = "and".join(f"=={_compact_literal(arg)}" for arg in args)
        if "if" in compact_code and and_compare_pattern in compact_code:
            suspicious_hits += 1

    if suspicious_hits >= 2:
        return "AntiCheat: potential hardcoded testcase mapping detected."

    return ""


def _compact_literal(value: object) -> str:
    return repr(value).replace(" ", "")


def _run_testcase(case: dict, namespace: dict, code: str) -> Tuple[bool, str]:
    kind = case.get("kind")

    if kind == "contains":
        required_text = case.get("text", "")
        ok = required_text in code
        return ok, f"Expected code to contain '{required_text}'"

    if kind == "not_contains":
        forbidden_text = case.get("text", "")
        ok = forbidden_text not in code
        return ok, f"Expected code not to contain '{forbidden_text}'"

    if kind == "call":
        fn_name = case.get("function")
        fn = namespace.get(fn_name)
        if not callable(fn):
            return False, f"Function '{fn_name}' not found"

        args = case.get("args", [])
        expected = case.get("expected")

        try:
            actual = invoke_callable(fn, *args)
        except ExecutionLimitExceeded as exc:
            return False, f"Function '{fn_name}' exceeded execution limit: {exc}"
        except Exception as exc:
            return False, f"Function '{fn_name}' raised {exc.__class__.__name__}: {exc}"

        if actual != expected:
            return False, f"{fn_name}{tuple(args)} expected {expected}, got {actual}"

        return True, ""

    if kind == "call_approx":
        fn_name = case.get("function")
        fn = namespace.get(fn_name)
        if not callable(fn):
            return False, f"Function '{fn_name}' not found"

        args = case.get("args", [])
        expected = float(case.get("expected", 0.0))
        tolerance = float(case.get("tolerance", 1e-6))

        try:
            actual = float(invoke_callable(fn, *args))
        except ExecutionLimitExceeded as exc:
            return False, f"Function '{fn_name}' exceeded execution limit: {exc}"
        except Exception as exc:
            return False, f"Function '{fn_name}' raised {exc.__class__.__name__}: {exc}"

        if abs(actual - expected) > tolerance:
            return (
                False,
                f"{fn_name}{tuple(args)} expected approximately {expected} (+/-{tolerance}), got {actual}",
            )

        return True, ""

    return False, "Unknown testcase kind"