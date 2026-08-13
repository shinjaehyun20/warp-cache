from __future__ import annotations

import argparse
import json
import platform
import statistics
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from warp_cache import WarpIndex


def percentile95(values: list[float]) -> float:
    return sorted(values)[min(len(values) - 1, int(len(values) * 0.95))]


def measure(index: WarpIndex, paths: list[Path], runs: int) -> list[float]:
    values = []
    for _ in range(runs):
        start = time.perf_counter()
        index.refresh(paths)
        values.append(time.perf_counter() - start)
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Reproducible WarpCache digest benchmark")
    parser.add_argument("--files", type=int, default=2000)
    parser.add_argument("--bytes-per-file", type=int, default=131072)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("artifacts/benchmark.json"))
    args = parser.parse_args()
    if args.files < 2 or args.bytes_per_file < 1 or args.runs < 3:
        parser.error("files >= 2, bytes-per-file >= 1, runs >= 3")

    with tempfile.TemporaryDirectory(prefix="warp-cache-benchmark-") as folder:
        root = Path(folder)
        block = (b"WarpCache-proof-carrying-reuse\n" * ((args.bytes_per_file // 32) + 1))[:args.bytes_per_file]
        paths = []
        for number in range(args.files):
            path = root / f"asset-{number:05d}.bin"
            path.write_bytes(block)
            paths.append(path)

        baseline = measure(WarpIndex(), paths, args.runs)
        warmed = WarpIndex()
        warmed.refresh(paths)
        cached = measure(warmed, paths, args.runs)

        changed = paths[len(paths) // 2]
        changed.write_bytes(block + b"changed")
        before = warmed.hashes_computed
        warmed.refresh(paths)
        changed_rehashed = warmed.hashes_computed == before + 1

    baseline_median = statistics.median(baseline)
    cached_median = statistics.median(cached)
    report = {
        "schema": "warp-cache-benchmark/v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "corpus": {"files": args.files, "bytes_per_file": args.bytes_per_file, "total_bytes": args.files * args.bytes_per_file},
        "runs": args.runs,
        "baseline_full_hash": {"seconds": [round(value, 6) for value in baseline], "median_seconds": round(baseline_median, 6), "p95_seconds": round(percentile95(baseline), 6)},
        "warp_cache_reuse": {"seconds": [round(value, 6) for value in cached], "median_seconds": round(cached_median, 6), "p95_seconds": round(percentile95(cached), 6), "hashes_reused": warmed.hashes_reused},
        "effect": {"seconds_saved": round(baseline_median - cached_median, 6), "reduction_percent": round((baseline_median-cached_median)/baseline_median*100, 2), "speed_multiplier": round(baseline_median/cached_median, 3)},
        "correctness": {"changed_file_rehashed": changed_rehashed},
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
