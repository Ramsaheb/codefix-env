def grade(code):
    score = 0.0

    if "SyntaxError" not in code:
        score += 0.3

    if "a+b" in code:
        score += 0.7

    return min(score, 1.0)