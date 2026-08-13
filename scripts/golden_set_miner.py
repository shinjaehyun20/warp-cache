#!/usr/bin/env python3
"""
golden_set_miner.py — Mines historical Portfolio DB artifacts and resolutions
to discover successful execution scripts, tools, and artifacts, then automatically
promotes them to the WarpCache Golden Set registry.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from warp_cache.golden_set import GoldenCase, GoldenSet, GoldenSetError


WORKSPACE_ROOT = Path(r"D:\workspace")
PORTFOLIO_DB_DIR = WORKSPACE_ROOT / "runtime" / "db"
ARTIFACTS_JSONL = PORTFOLIO_DB_DIR / "artifacts.jsonl"
RESOLUTIONS_JSONL = PORTFOLIO_DB_DIR / "resolutions.jsonl"
DEFAULT_REGISTRY = PROJECT_ROOT / "data" / "golden-set.json"


def find_canonical_script(paths: list[str]) -> Path | None:
    """Finds a canonical python or shell script that exists in the workspace.
    Filters out temp paths (like /tmp, /_tmp, /Downloads).
    """
    for p_str in paths:
        try:
            p = Path(p_str).resolve()
            if not p.is_file():
                continue
            
            # Avoid temp or downloads folders
            path_parts = [part.lower() for part in p.parts]
            if "tmp" in path_parts or "_tmp" in path_parts or "downloads" in path_parts:
                continue
                
            # Must be under workspace
            if not str(p).startswith(str(WORKSPACE_ROOT)):
                continue
                
            # Filter for script extensions
            if p.suffix in (".py", ".ps1", ".bat"):
                return p
        except Exception:
            continue
    return None


def mine_artifacts(registry: GoldenSet) -> int:
    if not ARTIFACTS_JSONL.exists():
        print(f"[WARN] Artifacts log not found: {ARTIFACTS_JSONL}")
        return 0

    promoted_count = 0
    print(f"Reading artifacts from {ARTIFACTS_JSONL}...")
    
    with ARTIFACTS_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            evidence_paths = record.get("evidence_paths", [])
            script_path = find_canonical_script(evidence_paths)
            if not script_path:
                continue

            # Map record to GoldenCase fields
            kind = "script"
            verifier = record.get("refs", {}).get("verifier") or record.get("refs", {}).get("task_id") or "verified_by_history"
            project_id = record.get("project_id", "unassigned")
            runtime = record.get("runtime", "unknown")
            
            graph_refs = [f"project:{project_id}", f"runtime:{runtime}"]
            if "wbs_id" in record.get("refs", {}):
                graph_refs.append(f"wbs:{record['refs']['wbs_id']}")

            summary = record.get("summary", "") or record.get("subject", "")
            
            # Use record's artifact_id as input fingerprint reference
            input_fingerprint = record.get("artifact_id", "historical-run")

            try:
                case = GoldenCase.promote(
                    kind=kind,
                    canonical_path=script_path,
                    input_fingerprint=input_fingerprint,
                    verifier_ref=str(verifier),
                    graph_refs=graph_refs,
                    summary=summary
                )
                res = registry.promote(case)
                if res.get("created"):
                    print(f"Promoted newly discovered script: {script_path.name} (Case ID: {res['case_id']})")
                    promoted_count += 1
            except GoldenSetError as e:
                # Script may be invalid or missing required fields
                continue
            except Exception as e:
                print(f"[ERROR] Failed promoting {script_path}: {e}")

    return promoted_count


def main() -> int:
    registry = GoldenSet(DEFAULT_REGISTRY)
    print(f"Initializing Golden Set Miner. Target Registry: {DEFAULT_REGISTRY}")
    
    promoted = mine_artifacts(registry)
    print(f"Mining complete. Promoted {promoted} new golden cases to registry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
