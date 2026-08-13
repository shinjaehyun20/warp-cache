from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.browser_benchmark import main


def test_browser_benchmark_execution(tmp_path):
    output_json = tmp_path / "browser_benchmark.json"

    # Save original sys.argv and mock it
    orig_argv = sys.argv
    sys.argv = ["browser_benchmark.py", "--runs", "3", "--output", str(output_json)]
    try:
        exit_code = main()
    finally:
        sys.argv = orig_argv

    assert exit_code == 0
    assert output_json.exists()

    # Validate output schema
    data = json.loads(output_json.read_text(encoding="utf-8"))
    assert data["schema"] == "warp-cache-browser-benchmark/v1"
    assert data["runs"] == 3
    assert "baseline_full_render" in data
    assert "warpcache_direct_bypass" in data
    assert "effect" in data
    assert "seconds_saved" in data["effect"]
    assert "reduction_percent" in data["effect"]
    assert "speed_multiplier" in data["effect"]
