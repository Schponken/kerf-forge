"""Test-wide settings."""
import os

# Viewer click-to-edit (kerf/attribution.py) rebuilds every part traced and once per param: ~30 s to minutes per
# viewer, and no test needs it through the pipeline (tests/test_attribution.py calls it directly). kerf verify sets
# the same switch for its project builds.
os.environ.setdefault("KERF_NO_ATTRIBUTION", "1")
