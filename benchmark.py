"""
Local benchmark — runs all tasks with the deterministic fallback policy
and reports scores without needing a running server.
"""

from dataclasses import dataclass
from typing import List

from env.environment import CodeFixEnvironment
from models import CodeFixAction
from tasks.task_loader import available_tasks


@dataclass
class BenchmarkResult:
    task: str
    solved: bool
    score: float
    steps: int
    max_steps: int
    error: str


def choose_benchmark_action(obs_dict: dict) -> str:
    code = str(obs_dict.get("code", ""))
    error = str(obs_dict.get("error", ""))

    if "SyntaxError" in error or "expected ':'" in error or "if a > b\n" in code:
        return "fix_syntax"

    if any(tok in code for tok in ("a-b", "a - b", "b-a", "b - a", "a-b+c", "b-a+c")):
        return "fix_logic"

    return "noop"


def run_task_benchmark(task_name: str) -> BenchmarkResult:
    env = CodeFixEnvironment()
    obs = env.reset(task=task_name)

    obs_dict = obs.model_dump()
    done = obs.done
    steps = 0
    max_steps = env.state.max_steps

    stagnation_steps = 0
    previous_code = obs_dict.get("code", "")

    while not done and steps < max_steps:
        action_str = choose_benchmark_action(obs_dict)
        obs = env.step(CodeFixAction(action=action_str))
        obs_dict = obs.model_dump()
        done = obs.done
        steps += 1

        current_code = obs_dict.get("code", "")
        reward = float(obs.reward or 0.0)

        if current_code == previous_code and reward <= 0:
            stagnation_steps += 1
        else:
            stagnation_steps = 0

        previous_code = current_code

        if stagnation_steps >= 2:
            break

    score = float(obs_dict.get("score", 0.0))
    solved = score >= 1.0
    return BenchmarkResult(
        task=task_name,
        solved=solved,
        score=score,
        steps=steps,
        max_steps=max_steps,
        error=str(obs_dict.get("error", "")),
    )


def compute_submission_readiness(results: List[BenchmarkResult]) -> float:
    if not results:
        return 0.0

    avg_score = sum(r.score for r in results) / len(results)
    solved_ratio = sum(1 for r in results if r.solved) / len(results)
    efficiency = sum(
        1.0 - (r.steps / max(r.max_steps, 1)) for r in results
    ) / len(results)

    readiness = (avg_score * 70.0) + (solved_ratio * 20.0) + (efficiency * 10.0)
    return round(max(0.0, min(readiness, 100.0)), 2)


def run_benchmark() -> tuple[List[BenchmarkResult], float]:
    tasks = available_tasks()
    results = [run_task_benchmark(t) for t in tasks]
    readiness = compute_submission_readiness(results)
    return results, readiness


def print_report(results: List[BenchmarkResult], readiness: float) -> None:
    print("CodeFixEnv Benchmark Results")
    print("=" * 72)
    print(f"{'Task':<12} {'Solved':<8} {'Score':<8} {'Steps':<10} {'Error'}")
    print("-" * 72)

    for r in results:
        solved_text = "yes" if r.solved else "no"
        step_text = f"{r.steps}/{r.max_steps}"
        print(f"{r.task:<12} {solved_text:<8} {r.score:<8.3f} {step_text:<10} {r.error}")

    print("-" * 72)
    print(f"Submission readiness score: {readiness}/100")

    if readiness >= 85:
        print("Status: Strong submission readiness")
    elif readiness >= 65:
        print("Status: Good baseline, improve harder tasks")
    else:
        print("Status: Needs more work before submission")


def main() -> None:
    results, readiness = run_benchmark()
    print_report(results, readiness)


if __name__ == "__main__":
    main()
