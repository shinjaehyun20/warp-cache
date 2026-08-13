from pathlib import Path
import subprocess
import sys


def test_cli_query_empty_registry(tmp_path: Path) -> None:
    run = subprocess.run(
        [sys.executable, "scripts/warp_cache.py", "golden-query", "--registry", str(tmp_path / "golden.json"), "--query", "weekly report"],
        cwd=Path(__file__).parents[1], text=True, capture_output=True, check=True,
    )
    assert '"candidate_count": 0' in run.stdout
