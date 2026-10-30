"""PostToolUse: after editing a part, project.yaml or the catalog, run the fast checks and report problems back."""
import json, os, re, subprocess, sys
root = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
path = (data.get("tool_input") or {}).get("file_path") or ""
rel = os.path.relpath(path, root) if path else ""
kerf = os.path.join(root, ".venv/bin/kerf")
if rel == os.path.join("catalog", "hardware.json"):
    try:
        cat = json.load(open(path))
    except Exception as e:
        print(f"catalog/hardware.json is not valid JSON: {e}", file=sys.stderr); sys.exit(2)
    def walk(node, path=""):
        out = []
        if isinstance(node, dict):
            if "source" in node:
                return out
            if path and any(isinstance(v, (int, float)) for v in node.values()):
                out.append(path)
            for k, v in node.items():
                if not k.startswith("_") and isinstance(v, dict):
                    out += walk(v, f"{path}.{k}" if path else k)
        return out
    bad = walk(cat)
    if bad:
        print(f"catalog entries need a 'source' URL: {bad[:10]}", file=sys.stderr); sys.exit(2)
    sys.exit(0)
m = re.match(r"projects/([^/]+)/(parts/[^/]+\.py|project\.yaml)$", rel)
if not m or not os.path.exists(kerf):
    sys.exit(0)
r = subprocess.run([kerf, "check", m.group(1), "--quick"], cwd=root, capture_output=True, text=True, timeout=880)
if r.returncode != 0:
    print(f"kerf check {m.group(1)} --quick FAILED after your edit:\n{r.stdout[-4000:]}{r.stderr[-1500:]}", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
