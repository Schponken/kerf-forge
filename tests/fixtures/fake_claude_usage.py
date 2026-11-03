"""A Claude Code stream-json run that is cut off by the usage limit (tests/test_usage_failsafe.py)."""
import json
print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-123"}), flush=True)
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "Drawing the hub."}]}}), flush=True)
print(json.dumps({"type": "result", "subtype": "success", "is_error": True, "session_id": "sess-123",
                  "result": "Claude AI usage limit reached|1893456000"}), flush=True)
