def compute_reward(previous_score: float, current_score: float) -> float:
    delta = round(current_score - previous_score, 3)

    if delta > 0:
        return delta

    if delta < 0:
        return -0.2

    return -0.01