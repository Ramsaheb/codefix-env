from models import CodeFixReward


def build_reward(
    previous_score: float,
    current_score: float,
    changed_lines: int,
    action_error: str,
    grade_error: str,
) -> CodeFixReward:
    delta = round(current_score - previous_score, 3)

    if delta > 0:
        efficiency_bonus = 0.05 if 0 < changed_lines <= 2 else 0.0
        value = round(min(delta + efficiency_bonus, 1.0), 3)
        return CodeFixReward(
            value=value,
            previous_score=round(previous_score, 3),
            current_score=round(current_score, 3),
            delta=delta,
            changed_lines=changed_lines,
            action_error=action_error,
            grade_error=grade_error,
        )

    penalty = -0.01

    if changed_lines == 0:
        penalty -= 0.02

    if action_error:
        penalty -= 0.08

    if delta < 0:
        penalty -= 0.12
        if grade_error:
            penalty -= 0.04

    value = round(max(penalty, -0.5), 3)
    return CodeFixReward(
        value=value,
        previous_score=round(previous_score, 3),
        current_score=round(current_score, 3),
        delta=delta,
        changed_lines=changed_lines,
        action_error=action_error,
        grade_error=grade_error,
    )


def compute_reward(
    previous_score: float,
    current_score: float,
    changed_lines: int,
    action_error: str,
    grade_error: str,
) -> float:
    return build_reward(
        previous_score=previous_score,
        current_score=current_score,
        changed_lines=changed_lines,
        action_error=action_error,
        grade_error=grade_error,
    ).value