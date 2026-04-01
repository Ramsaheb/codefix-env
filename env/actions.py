from typing import Dict, Tuple


BASIC_ACTIONS = {"fix_syntax", "fix_logic", "noop"}


def parse_action(raw_action: str) -> Tuple[str, Dict[str, object]]:
	if not isinstance(raw_action, str) or not raw_action.strip():
		raise ValueError("Action must be a non-empty string.")

	action = raw_action.strip()
	normalized = action.lower()

	if normalized in BASIC_ACTIONS:
		return normalized, {}

	if normalized.startswith("replace_line:"):
		parts = action.split(":", 2)
		if len(parts) != 3:
			raise ValueError("replace_line format must be: replace_line:<line_no>:<new_code>")

		line_no = _parse_line_no(parts[1], command_name="replace_line")
		return "replace_line", {"line_no": line_no, "new_code": parts[2]}

	if normalized.startswith("append_line:"):
		parts = action.split(":", 1)
		if len(parts) != 2:
			raise ValueError("append_line format must be: append_line:<new_code>")
		return "append_line", {"new_code": parts[1]}

	if normalized.startswith("delete_line:"):
		parts = action.split(":", 1)
		if len(parts) != 2:
			raise ValueError("delete_line format must be: delete_line:<line_no>")

		line_no = _parse_line_no(parts[1], command_name="delete_line")
		return "delete_line", {"line_no": line_no}

	if normalized.startswith("replace_text:"):
		parts = action.split(":", 2)
		if len(parts) != 3:
			raise ValueError(
				"replace_text format must be: replace_text:<old_text>:<new_text>"
			)

		old_text = parts[1]
		if not old_text:
			raise ValueError("replace_text old_text must be non-empty.")

		return "replace_text", {"old_text": old_text, "new_text": parts[2]}

	raise ValueError(f"Unsupported action '{action}'.")


def _parse_line_no(raw_line_no: str, command_name: str) -> int:
	try:
		line_no = int(raw_line_no)
	except ValueError as exc:
		raise ValueError(f"{command_name} line_no must be an integer.") from exc

	if line_no < 1:
		raise ValueError(f"{command_name} line_no must be >= 1.")

	return line_no
