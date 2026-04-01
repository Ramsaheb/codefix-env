from typing import Dict, Tuple


BASIC_ACTIONS = {"fix_syntax", "fix_logic", "noop"}


def parse_action(raw_action: str) -> Tuple[str, Dict[str, object]]:
	if not isinstance(raw_action, str) or not raw_action.strip():
		raise ValueError("Action must be a non-empty string.")

	action = raw_action.strip()

	if action in BASIC_ACTIONS:
		return action, {}

	if action.startswith("replace_line:"):
		parts = action.split(":", 2)
		if len(parts) != 3:
			raise ValueError("replace_line format must be: replace_line:<line_no>:<new_code>")

		try:
			line_no = int(parts[1])
		except ValueError as exc:
			raise ValueError("replace_line line_no must be an integer.") from exc

		if line_no < 1:
			raise ValueError("replace_line line_no must be >= 1.")

		return "replace_line", {"line_no": line_no, "new_code": parts[2]}

	raise ValueError(f"Unsupported action '{action}'.")
