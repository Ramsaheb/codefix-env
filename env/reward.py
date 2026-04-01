def compute_reward(
    previous_score: float,
    current_score: float,
    changed_lines: int,
    action_error: str,
    grade_error: str,
) -> float:
    delta = round(current_score - previous_score, 3)

    if delta > 0:
        efficiency_bonus = 0.05 if 0 < changed_lines <= 2 else 0.0
        return round(min(delta + efficiency_bonus, 1.0), 3)

    penalty = -0.01

    if changed_lines == 0:
        penalty -= 0.02

    if action_error:
        penalty -= 0.08

    if delta < 0:
        penalty -= 0.12
        if grade_error:
            penalty -= 0.04

    return round(max(penalty, -0.5), 3)