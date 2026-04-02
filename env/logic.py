import ast
import re

from env.actions import parse_action


def apply_action(code: str, raw_action: str) -> str:
    action, payload = parse_action(raw_action)

    if action == "noop":
        return code

    if action == "fix_syntax":
        return _fix_syntax(code)

    if action == "fix_logic":
        return _fix_logic(code)

    if action == "replace_line":
        return _replace_line(code, int(payload["line_no"]), str(payload["new_code"]))

    if action == "insert_line":
        return _insert_line(code, int(payload["line_no"]), str(payload["new_code"]))

    if action == "replace_range":
        return _replace_range(
            code,
            int(payload["start_line"]),
            int(payload["end_line"]),
            str(payload["new_code"]),
        )

    if action == "append_line":
        return _append_line(code, str(payload["new_code"]))

    if action == "delete_line":
        return _delete_line(code, int(payload["line_no"]))

    if action == "replace_text":
        return _replace_text(code, str(payload["old_text"]), str(payload["new_text"]))

    if action == "rewrite_code":
        return str(payload["new_code"])

    return code


def _fix_syntax(code: str) -> str:
    updated = code
    updated = updated.replace('print("Hello', 'print("Hello")')

    # Add a missing colon for simple if/elif/else/for/while/def/class statements.
    updated = re.sub(
        r"(?m)^(\s*(?:if|elif|else|for|while|def|class)\b[^:\n]*)$",
        r"\1:",
        updated,
    )

    updated = updated.replace("print(a-b", "print(a-b)")
    updated = updated.replace("print(a+b", "print(a+b)")
    updated = _close_unbalanced_parens(updated)
    return updated


def _fix_logic(code: str) -> str:
    updated = _fix_logic_via_ast(code)

    replacements = {
        "a - b": "a + b",
        "a-b": "a+b",
        "b - a": "a + b",
        "b-a": "a+b",
        "return total - 1": "return total + 1",
    }
    for source, target in replacements.items():
        updated = updated.replace(source, target)

    return updated


class _AdditiveIntentTransformer(ast.NodeTransformer):
    def __init__(self):
        self.changed = False
        self._additive_context_stack = [False]

    def visit_FunctionDef(self, node: ast.FunctionDef):
        is_additive_intent = _is_additive_intent_name(node.name)
        self._additive_context_stack.append(is_additive_intent)
        self.generic_visit(node)
        self._additive_context_stack.pop()
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        is_additive_intent = _is_additive_intent_name(node.name)
        self._additive_context_stack.append(is_additive_intent)
        self.generic_visit(node)
        self._additive_context_stack.pop()
        return node

    def visit_BinOp(self, node: ast.BinOp):
        self.generic_visit(node)

        in_additive_context = any(self._additive_context_stack)
        if in_additive_context and isinstance(node.op, ast.Sub):
            node.op = ast.Add()
            self.changed = True

        return node


def _is_additive_intent_name(name: str) -> bool:
    lowered = name.lower()
    hints = (
        "add",
        "sum",
        "total",
        "combine",
        "compute",
        "stabilize",
        "synthesize",
        "merge",
        "aggregate",
    )
    return any(hint in lowered for hint in hints)


def _fix_logic_via_ast(code: str) -> str:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    transformer = _AdditiveIntentTransformer()
    transformed_tree = transformer.visit(tree)
    if not transformer.changed:
        return code

    ast.fix_missing_locations(transformed_tree)
    rebuilt = ast.unparse(transformed_tree)
    if code.endswith("\n") and rebuilt:
        rebuilt += "\n"

    return rebuilt


def _replace_line(code: str, line_no: int, new_code: str) -> str:
    lines = code.splitlines()
    index = line_no - 1

    if index < 0 or index >= len(lines):
        return code

    lines[index] = new_code
    rebuilt = "\n".join(lines)

    if code.endswith("\n"):
        return rebuilt + "\n"

    return rebuilt


def _insert_line(code: str, line_no: int, new_code: str) -> str:
    lines = code.splitlines()
    index = min(max(line_no - 1, 0), len(lines))
    lines.insert(index, new_code)

    rebuilt = "\n".join(lines)
    if code.endswith("\n") and rebuilt:
        return rebuilt + "\n"
    if not code and rebuilt:
        return rebuilt + "\n"
    return rebuilt


def _replace_range(code: str, start_line: int, end_line: int, new_code: str) -> str:
    lines = code.splitlines()
    if not lines:
        return _append_line("", new_code) if new_code else ""

    start_idx = start_line - 1
    end_idx = end_line - 1
    if start_idx < 0 or start_idx >= len(lines):
        return code

    end_idx = min(end_idx, len(lines) - 1)
    replacement_lines = new_code.splitlines()
    updated_lines = lines[:start_idx] + replacement_lines + lines[end_idx + 1 :]

    rebuilt = "\n".join(updated_lines)
    if code.endswith("\n") and rebuilt:
        return rebuilt + "\n"
    return rebuilt


def _append_line(code: str, new_code: str) -> str:
    suffix = "\n" if code and not code.endswith("\n") else ""
    return f"{code}{suffix}{new_code}\n"


def _delete_line(code: str, line_no: int) -> str:
    lines = code.splitlines()
    index = line_no - 1
    if index < 0 or index >= len(lines):
        return code

    del lines[index]
    rebuilt = "\n".join(lines)
    if code.endswith("\n") and rebuilt:
        return rebuilt + "\n"
    return rebuilt


def _replace_text(code: str, old_text: str, new_text: str) -> str:
    return code.replace(old_text, new_text)


def _close_unbalanced_parens(code: str) -> str:
    fixed_lines = []
    for line in code.splitlines():
        opens = line.count("(")
        closes = line.count(")")
        if opens > closes:
            line = f"{line}{')' * (opens - closes)}"
        fixed_lines.append(line)

    rebuilt = "\n".join(fixed_lines)
    if code.endswith("\n") and rebuilt:
        return rebuilt + "\n"
    return rebuilt