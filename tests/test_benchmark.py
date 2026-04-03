"""Benchmark integration tests."""

from benchmark import compute_submission_readiness, run_benchmark


def test_benchmark_runs_all_registered_tasks():
    results, readiness = run_benchmark()

    task_names = {r.task for r in results}
    assert {"easy", "medium", "hard", "expert", "nightmare"}.issubset(task_names)
    assert 0.0 <= readiness <= 100.0


def test_readiness_formula_is_bounded():
    class DummyResult:
        def __init__(self, score, solved, steps, max_steps):
            self.score = score
            self.solved = solved
            self.steps = steps
            self.max_steps = max_steps

    readiness = compute_submission_readiness(
        [
            DummyResult(score=1.0, solved=True, steps=1, max_steps=8),
            DummyResult(score=0.0, solved=False, steps=8, max_steps=8),
        ]
    )
    assert 0.0 <= readiness <= 100.0
