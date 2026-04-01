from typing import Dict, List


TEST_CASES: Dict[str, List[dict]] = {
	"easy": [
		{"kind": "contains", "text": 'print("Hello")'},
	],
	"medium": [
		{"kind": "call", "function": "add", "args": [2, 3], "expected": 5},
		{"kind": "call", "function": "add", "args": [-1, 4], "expected": 3},
	],
	"hard": [
		{"kind": "call", "function": "compute", "args": [5, 2], "expected": 7},
		{"kind": "call", "function": "compute", "args": [1, 4], "expected": 5},
	],
}


def get_testcases(task_name: str) -> List[dict]:
	return TEST_CASES.get(task_name, [])
