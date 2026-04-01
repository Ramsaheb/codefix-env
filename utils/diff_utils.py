import difflib
from typing import Dict


def is_improved(old_code: str, new_code: str) -> bool:
    return old_code != new_code


def diff_summary(old_code: str, new_code: str) -> Dict[str, object]:
    if old_code == new_code:
        return {"changed_lines": 0, "preview": ""}

    diff_lines = list(
        difflib.unified_diff(
            old_code.splitlines(),
            new_code.splitlines(),
            fromfile="before.py",
            tofile="after.py",
            lineterm="",
        )
    )

    changed_lines = 0
    for line in diff_lines:
        if line.startswith(("---", "+++", "@@")):
            continue
        if line.startswith("-") or line.startswith("+"):
            changed_lines += 1

    preview = "\n".join(diff_lines[:10])
    return {"changed_lines": changed_lines, "preview": preview}