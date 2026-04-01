def compute_reward(old_code, new_code):
    reward = 0.0

    if "SyntaxError" not in new_code:
        reward += 0.3

    if "a+b" in new_code:
        reward += 0.7

    return min(reward, 1.0)