#!/usr/bin/env python3
"""
warp_cache_preflight.py — Preflight query check script for other runtimes.
Queries the Golden Set registry to find reusable scripts/tools before creating new ones.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from warp_cache.golden_set import GoldenSet

DEFAULT_REGISTRY = PROJECT_ROOT / "data" / "golden-set.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="WarpCache Preflight Gate for runtimes")
    parser.add_argument("query", help="Intent query to search for reusable cases")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()

    if not args.registry.exists():
        print(
            json.dumps(
                {
                    "outcome": "MISS",
                    "reason": f"Registry database not found at {args.registry}",
                    "candidates": []
                },
                ensure_ascii=False,
                indent=2
            )
        )
        return 1

    registry = GoldenSet(args.registry)
    try:
        result = registry.reuse_candidates(args.query, limit=args.limit)
    except Exception as e:
        print(json.dumps({"outcome": "ERROR", "reason": str(e), "candidates": []}, ensure_ascii=False, indent=2))
        return 2

    # Filter for eligible (currently valid, matching file hash) candidates
    eligible_candidates = [
        c for c in result.get("candidates", []) if c.get("reuse_state") == "eligible"
    ]

    if eligible_candidates:
        output = {
            "outcome": "HIT",
            "reason": f"Found {len(eligible_candidates)} eligible reusable cases",
            "candidates": eligible_candidates
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    else:
        output = {
            "outcome": "MISS",
            "reason": "No eligible reusable candidates found for this query",
            "candidates": []
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
