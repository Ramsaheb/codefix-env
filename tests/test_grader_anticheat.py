from graders.grader import grade_code


def test_grader_penalizes_hardcoded_testcase_mapping():
    candidate_code = (
        "def add(a, b):\n"
        "    if (a, b) == (2, 3):\n"
        "        return 5\n"
        "    if (a, b) == (-1, 4):\n"
        "        return 3\n"
        "    if (a, b) == (0, 0):\n"
        "        return 0\n"
        "    if (a, b) == (10, -5):\n"
        "        return 5\n"
        "    return 0\n"
    )

    score, error = grade_code("medium", candidate_code)

    assert score <= 0.2
    assert "anticheat" in error.lower()
