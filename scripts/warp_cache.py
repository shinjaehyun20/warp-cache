from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from warp_cache.golden_set import GoldenCase, GoldenSet, GoldenSetError
from warp_cache.har_contract import HarContractError, derive_endpoint_contract_file


def main() -> int:
    parser = argparse.ArgumentParser(description="WarpCache Golden Set reuse gate")
    sub = parser.add_subparsers(dest="command", required=True)
    query = sub.add_parser("golden-query", help="return currently reusable verified cases")
    query.add_argument("--registry", type=Path, default=PROJECT_ROOT / "data" / "golden-set.json")
    query.add_argument("--query", required=True)
    query.add_argument("--limit", type=int, default=5)
    derive = sub.add_parser("har-derive-contract", help="derive a secret-free endpoint contract; never stores raw HAR")
    derive.add_argument("--input", type=Path, required=True, help="local HAR input; it is read only")
    derive.add_argument("--output", type=Path, required=True, help="safe derived endpoint-contract JSON")
    promote = sub.add_parser("golden-promote", help="promote a canonical verified item")
    promote.add_argument("--registry", type=Path, default=PROJECT_ROOT / "data" / "golden-set.json")
    promote.add_argument("--kind", required=True, choices=("skill", "tool", "script", "artifact", "endpoint_contract"))
    promote.add_argument("--canonical-path", required=True)
    promote.add_argument("--input-fingerprint", required=True)
    promote.add_argument("--verifier-ref", required=True)
    promote.add_argument("--graph-ref", action="append", required=True)
    promote.add_argument("--summary", required=True)
    args = parser.parse_args()
    try:
        if args.command == "har-derive-contract":
            contract = derive_endpoint_contract_file(args.input, args.output)
            payload = {
                "outcome": "SAFE_ENDPOINT_CONTRACT_WRITTEN",
                "output": str(args.output),
                "endpoint_count": contract["endpoint_count"],
                "raw_content_persisted": False,
            }
        else:
            registry = GoldenSet(args.registry)
            if args.command == "golden-query":
                payload = registry.reuse_candidates(args.query, limit=max(1, min(args.limit, 20)))
            else:
                case = GoldenCase.promote(
                    kind=args.kind, canonical_path=args.canonical_path,
                    input_fingerprint=args.input_fingerprint, verifier_ref=args.verifier_ref,
                    graph_refs=args.graph_ref, summary=args.summary,
                )
                payload = registry.promote(case)
    except (GoldenSetError, HarContractError, OSError, ValueError) as exc:
        print(json.dumps({"outcome": "UNPROVEN", "reason": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
