from dataclasses import dataclass
from typing import List

from env.environment import CodeFixEnv
from tasks.task_loader import available_tasks


@dataclass
class BenchmarkResult:
    task: str
    solved: bool
    score: float
    steps: int
    max_steps: int
    error: str


def choose_benchmark_action(state: dict) -> str:
    code = str(state.get("code", ""))
    error = str(state.get("error", ""))

    if "SyntaxError" in error or "expected ':'" in error or "if a > b\n" in code:
        return "fix_syntax"

    if any(token in code for token in ["a-b", "a - b", "b-a", "b - a", "a-b+c", "b-a+c"]):
        return "fix_logic"

    return "noop"


def run_task_benchmark(task_name: str) -> BenchmarkResult:
    env = CodeFixEnv()
    state = env.reset(task_name)

    done = False
    steps = 0
    max_steps = int(state.get("step_count", 0))
    max_steps = env.state.max_steps if env.state is not None else 8

    stagnation_steps = 0
    previous_code = str(state.get("code", ""))

    while not done and steps < max_steps:
        action = choose_benchmark_action(state)
        state, reward, done, info = env.step(action)
        steps += 1

        current_code = str(state.get("code", ""))
        if current_code == previous_code and reward <= 0:
            stagnation_steps += 1
        else:
            stagnation_steps = 0

        previous_code = current_code

        if stagnation_steps >= 2:
            break

    score = float(state.get("score", 0.0))
    solved = score >= 1.0
    return BenchmarkResult(
        task=task_name,
        solved=solved,
        score=score,
        steps=steps,
        max_steps=max_steps,
        error=str(state.get("error", "")),
    )


def compute_submission_readiness(results: List[BenchmarkResult]) -> float:
    if not results:
        return 0.0

    avg_score = sum(result.score for result in results) / len(results)
    solved_ratio = sum(1 for result in results if result.solved) / len(results)
    efficiency = sum(1.0 - (result.steps / max(result.max_steps, 1)) for result in results) / len(results)

    readiness = (avg_score * 70.0) + (solved_ratio * 20.0) + (efficiency * 10.0)
    return round(max(0.0, min(readiness, 100.0)), 2)


def run_benchmark() -> tuple[List[BenchmarkResult], float]:
    tasks = available_tasks()
    results = [run_task_benchmark(task_name) for task_name in tasks]
    readiness = compute_submission_readiness(results)
    return results, readiness


def print_report(results: List[BenchmarkResult], readiness: float) -> None:
    print("CodeFixEnv Benchmark Results")
    print("=" * 72)
    print(f"{'Task':<12} {'Solved':<8} {'Score':<8} {'Steps':<10} {'Error'}")
    print("-" * 72)

    for result in results:
        solved_text = "yes" if result.solved else "no"
        step_text = f"{result.steps}/{result.max_steps}"
        print(f"{result.task:<12} {solved_text:<8} {result.score:<8.3f} {step_text:<10} {result.error}")

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
