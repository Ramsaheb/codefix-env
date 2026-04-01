from typing import Dict, List


TEST_CASES: Dict[str, List[dict]] = {
    "easy": [
        {"kind": "contains", "text": 'print("Hello")'},
    ],
    "medium": [
        {"kind": "call", "function": "add", "args": [2, 3], "expected": 5},
        {"kind": "call", "function": "add", "args": [-1, 4], "expected": 3},
        {"kind": "call", "function": "add", "args": [0, 0], "expected": 0},
        {"kind": "call", "function": "add", "args": [10, -5], "expected": 5},
    ],
    "hard": [
        {"kind": "call", "function": "compute", "args": [5, 2], "expected": 7},
        {"kind": "call", "function": "compute", "args": [1, 4], "expected": 5},
        {"kind": "call", "function": "compute", "args": [0, 0], "expected": 0},
        {"kind": "call", "function": "compute", "args": [-3, 8], "expected": 5},
    ],
    "expert": [
        {"kind": "call", "function": "stabilize", "args": [20, 5], "expected": 25},
        {"kind": "call", "function": "stabilize", "args": [60, 50], "expected": 100},
        {"kind": "call", "function": "stabilize", "args": [-5, 1], "expected": 0},
        {"kind": "call", "function": "stabilize", "args": [0, 0], "expected": 0},
    ],
    "nightmare": [
        {"kind": "call", "function": "synthesize", "args": [5, 2, 1], "expected": 8},
        {"kind": "call", "function": "synthesize", "args": [1, 4, 2], "expected": 7},
        {"kind": "call", "function": "synthesize", "args": [-3, 8, 5], "expected": 10},
        {"kind": "call", "function": "synthesize", "args": [0, 0, 0], "expected": 0},
    ],
}


def get_testcases(task_name: str) -> List[dict]:
    return TEST_CASES.get(task_name, [])
