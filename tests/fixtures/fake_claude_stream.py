"""Prints a short Claude Code stream-json design run, one event every DELAY seconds (thought web live test)."""
import json, sys, time
DELAY = float(sys.argv[1]) if len(sys.argv) > 1 else 0.15
def tool(name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}
def text(t):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}
EVENTS = [
    tool("Agent", description="Research morphing-wing drones", subagent_type="design-researcher", prompt="..."),
    tool("WebSearch", query="morphing wing drone folding wings like a hawk EPFL"),
    tool("WebFetch", url="https://www.epfl.ch/labs/lis/research/lishawk/", prompt="how the wings fold"),
    text("LisHawk sweeps feathered wings for agility; a rigid pivoting panel is simpler to print."),
    tool("WebSearch", query="variable sweep wing pivot servo torque"),
    tool("WebSearch", query="feathered telescoping printed wing"),
    tool("WebSearch", query="2806.5 motor thrust 4S 7 inch prop"),
    tool("WebFetch", url="https://shop.iflight.com/xing2-2806-5-motor-pro1180", prompt="thrust table"),
    tool("Read", file_path="/repo/projects/fpv_wing/DESIGN.md"),
    tool("Read", file_path="/repo/catalog/hardware.json"),
    tool("Write", file_path="/repo/projects/demo/DESIGN.md", content="..."),
    tool("Write", file_path="/repo/projects/demo/parts/hub.py", content="..."),
    tool("Bash", command=".venv/bin/kerf check demo --quick", description="check"),
    {"type": "result", "subtype": "success", "duration_ms": 1000, "result": "done"},
]
for e in EVENTS:
    print(json.dumps(e), flush=True)
    time.sleep(DELAY)
