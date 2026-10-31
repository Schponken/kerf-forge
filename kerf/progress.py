"""Machine-readable progress for Kerf Studio: with KERF_PROGRESS=1 the pipeline prints one `@@{json}` line per event
(stage started, part checked, sweep done, requirement result, finished). Off by default: CLI output is unchanged."""
from __future__ import annotations

import json
import os
import time

STAGES = [("build", "Build parts"), ("print", "Print checks"), ("fit", "Fit, screws, access"), ("motion", "Motion sweeps"),
          ("requirements", "Engineering checks"), ("export", "Files + plates"), ("renders", "Renders")]


def on() -> bool:
    return os.environ.get("KERF_PROGRESS") == "1"


def emit(kind: str, **kw):
    if on():
        print("@@" + json.dumps({"k": kind, "t": round(time.time(), 2), **kw}, default=str), flush=True)


def stage(key: str):
    emit("stage", stage=key)
