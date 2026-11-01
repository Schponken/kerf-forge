"""Design-intent lint for part code: every boolean on a part's body (the variable handed to ctx.finish) must say why.

A feature explains itself when it goes through ctx.add / ctx.cut (with why=), comes from an iface / idioms / features /
sections call (those register themselves or carry their reason in their docstring), or has a `# why:` comment on the
statement or the line directly above it. `unexplained(src)` lists the rest; the after-edit hook
(.claude/hooks/after_edit.py) reports them to the editing agent after every part edit.
"""
from __future__ import annotations

import ast

SELF_EXPLAINING = ("iface", "idioms", "features", "sections", "F", "I")   # module aliases whose calls carry intent


def _finish_vars(tree) -> set:
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "finish" and n.args:
            if isinstance(n.args[0], ast.Name):
                out.add(n.args[0].id)
    return out


def _explained_call(node) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and f.attr in ("add", "cut") and isinstance(f.value, ast.Name) and f.value.id == "ctx":
                return True
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in SELF_EXPLAINING:
                return True
    return False


def _is_boolean(node, target: str) -> bool:
    if isinstance(node, ast.AugAssign):
        return isinstance(node.op, (ast.Add, ast.Sub, ast.BitAnd))
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.BinOp):
        return isinstance(node.value.op, (ast.Add, ast.Sub, ast.BitAnd))
    return False


def unexplained(src: str) -> list[tuple[int, str]]:
    """[(line number, source line)] of body booleans with no why= / self-explaining call / `# why:` comment."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    lines = src.splitlines()
    bodies = _finish_vars(tree)
    out = []
    for n in ast.walk(tree):
        tgt = None
        if isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            tgt = n.target.id
        elif isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            tgt = n.targets[0].id
        if tgt not in bodies or not _is_boolean(n, tgt) or _explained_call(n.value):
            continue
        a, b = n.lineno, getattr(n, "end_lineno", n.lineno)
        span = lines[max(a - 2, 0):b]                    # the statement and the line above it
        if any("# why:" in l for l in span):
            continue
        out.append((a, lines[a - 1].strip()))
    return out
