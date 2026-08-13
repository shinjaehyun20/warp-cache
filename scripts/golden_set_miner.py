#!/usr/bin/env python3
"""
golden_set_miner.py — Mines historical Portfolio DB artifacts and devlogs
to discover successful execution scripts, tools, and artifacts, then automatically
promotes them to the WarpCache Golden Set registry.
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from warp_cache.golden_set import GoldenCase, GoldenSet, GoldenSetError

WORKSPACE_ROOT = Path(r"D:\workspace")
PORTFOLIO_DB_DIR = WORKSPACE_ROOT / "runtime" / "db"
ARTIFACTS_JSONL = PORTFOLIO_DB_DIR / "artifacts.jsonl"
DEVLOG_DIR = Path(r"F:\Obsidian\Jaehyun\01.Log\01.devLog")
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

            kind = "script"
            verifier = record.get("refs", {}).get("verifier") or record.get("refs", {}).get("task_id") or "verified_by_history"
            project_id = record.get("project_id", "unassigned")
            runtime = record.get("runtime", "unknown")

            graph_refs = [f"project:{project_id}", f"runtime:{runtime}"]
            if "wbs_id" in record.get("refs", {}):
                graph_refs.append(f"wbs:{record['refs']['wbs_id']}")

            summary = record.get("summary", "") or record.get("subject", "")
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
            except GoldenSetError:
                continue
            except Exception as e:
                print(f"[ERROR] Failed promoting {script_path}: {e}")

    return promoted_count


def mine_devlogs(registry: GoldenSet) -> int:
    if not DEVLOG_DIR.exists():
        print(f"[WARN] Devlog directory not found: {DEVLOG_DIR}")
        return 0

    promoted_count = 0
    print(f"Reading devlogs recursively from {DEVLOG_DIR}...")

    # Pattern to match script invocation patterns in devlogs
    cmd_pattern = re.compile(
        r"`(?:python|py\s+-3.11|powershell)?\s*([^`\s]+\.(?:py|ps1|bat))[^`]*`|```(?:bash|powershell|sh|cmd|text)?\n(.*?)\n```",
        re.IGNORECASE | re.DOTALL
    )

    for root, _, files in os.walk(str(DEVLOG_DIR)):
        for file in files:
            if not file.endswith(".md"):
                continue
            file_path = Path(root) / file

            # Google Drive sync encoding safety
            unicodedata.normalize("NFC", str(file_path))

            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception:
                continue

            matches = cmd_pattern.findall(content)
            for inline_file, block_content in matches:
                candidates = []
                if inline_file:
                    candidates.append(inline_file.strip())
                if block_content:
                    for line in block_content.splitlines():
                        line = line.strip()
                        parts = line.split()
                        for part in parts:
                            if part.endswith((".py", ".ps1", ".bat")):
                                candidates.append(part)

                for raw_candidate in candidates:
                    clean_path = raw_candidate.strip("'\"()[]{}")
                    candidate_file = WORKSPACE_ROOT / clean_path

                    if not candidate_file.is_file():
                        try:
                            candidate_file = Path(clean_path).resolve()
                        except Exception:
                            continue

                    if not candidate_file.is_file():
                        continue

                    # Hygiene filtering
                    path_parts = [part.lower() for part in candidate_file.parts]
                    if "tmp" in path_parts or "_tmp" in path_parts or "downloads" in path_parts:
                        continue

                    if not str(candidate_file).startswith(str(WORKSPACE_ROOT)):
                        continue

                    kind = "script"
                    verifier = f"devlog:{file}"
                    input_fingerprint = f"devlog-run-{file_path.stem}"
                    graph_refs = ["project:shared", "runtime:shared", "source:devlog"]
                    summary = f"Successful script run mined from devlog: {file}"

                    try:
                        case = GoldenCase.promote(
                            kind=kind,
                            canonical_path=candidate_file,
                            input_fingerprint=input_fingerprint,
                            verifier_ref=verifier,
                            graph_refs=graph_refs,
                            summary=summary
                        )
                        res = registry.promote(case)
                        if res.get("created"):
                            print(f"Promoted mined script from devlog: {candidate_file.name} (Case ID: {res['case_id']})")
                            promoted_count += 1
                    except GoldenSetError:
                        continue
                    except Exception as e:
                        print(f"[ERROR] Failed promoting mined script {candidate_file}: {e}")

    return promoted_count


def main() -> int:
    registry = GoldenSet(DEFAULT_REGISTRY)
    print(f"Initializing Golden Set Miner. Target Registry: {DEFAULT_REGISTRY}")

    promoted_artifacts = mine_artifacts(registry)
    promoted_devlogs = mine_devlogs(registry)
    
    total = promoted_artifacts + promoted_devlogs
    print(f"Mining complete. Promoted {total} new golden cases (Artifacts: {promoted_artifacts}, Devlogs: {promoted_devlogs}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
