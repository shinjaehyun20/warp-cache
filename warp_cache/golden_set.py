from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "warp-cache-golden-set/v1"
ALLOWED_KINDS = {"skill", "tool", "script", "artifact"}


class GoldenSetError(ValueError):
    pass


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    kind: str
    canonical_path: str
    sha256: str
    input_fingerprint: str
    verifier_ref: str
    graph_refs: tuple[str, ...]
    summary: str
    promoted_at: str

    @classmethod
    def promote(
        cls, *, kind: str, canonical_path: str | Path, input_fingerprint: str,
        verifier_ref: str, graph_refs: list[str], summary: str,
    ) -> "GoldenCase":
        if kind not in ALLOWED_KINDS:
            raise GoldenSetError(f"kind must be one of {sorted(ALLOWED_KINDS)}")
        path = Path(canonical_path).resolve(strict=True)
        if not path.is_file():
            raise GoldenSetError("canonical_path must be a regular file")
        if not input_fingerprint.strip() or not verifier_ref.strip() or not summary.strip():
            raise GoldenSetError("input_fingerprint, verifier_ref and summary are required")
        if (
            not isinstance(graph_refs, (list, tuple))
            or not graph_refs
            or any(not isinstance(value, str) or not value.strip() for value in graph_refs)
        ):
            raise GoldenSetError("at least one non-empty graph reference is required")
        checksum = sha256_file(path)
        identity = "\0".join((kind, str(path), checksum, input_fingerprint, verifier_ref))
        return cls(
            case_id="golden-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20],
            kind=kind, canonical_path=str(path), sha256=checksum,
            input_fingerprint=input_fingerprint, verifier_ref=verifier_ref,
            graph_refs=tuple(sorted(set(graph_refs))), summary=summary[:600], promoted_at=now_iso(),
        )


class GoldenSet:
    """Append-safe registry for verified, reusable work cases.

    It deliberately stores pointers, hashes and verification references—not
    source bodies or transient temp paths. A stale case is demoted at query
    time when its canonical source hash no longer matches.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": SCHEMA, "cases": []}
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if payload.get("schema") != SCHEMA or not isinstance(payload.get("cases"), list):
            raise GoldenSetError("incompatible Golden Set registry")
        return payload

    def promote(self, case: GoldenCase) -> dict[str, Any]:
        payload = self._load()
        by_id = {row.get("case_id"): row for row in payload["cases"] if isinstance(row, dict)}
        prior = by_id.get(case.case_id)
        by_id[case.case_id] = asdict(case)
        payload = {"schema": SCHEMA, "updated_at": now_iso(), "case_count": len(by_id), "cases": [by_id[key] for key in sorted(by_id)]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"case_id": case.case_id, "created": prior is None, "registry": str(self.path), "case_count": len(by_id)}

    def reuse_candidates(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise GoldenSetError("limit must be an integer from 1 to 20")
        terms = {term.casefold() for term in query.split() if term}
        candidates = []
        for row in self._load()["cases"]:
            if not isinstance(row, dict):
                continue
            haystack = " ".join([
                str(row.get("summary", "")),
                str(row.get("kind", "")),
                str(row.get("canonical_path", "")),
                *row.get("graph_refs", [])
            ]).casefold()
            score = sum(term in haystack for term in terms)
            path = Path(str(row.get("canonical_path", "")))
            current = path.is_file() and sha256_file(path) == row.get("sha256")
            if score and current:
                candidates.append({**row, "score": score, "reuse_state": "eligible"})
            elif score:
                candidates.append({**row, "score": score, "reuse_state": "stale_source"})
        candidates.sort(key=lambda row: (row["reuse_state"] != "eligible", -row["score"], row["case_id"]))
        return {"schema": "warp-cache-reuse-candidates/v1", "query": query, "candidate_count": min(len(candidates), limit), "candidates": candidates[:limit], "policy": "Only eligible cases may be reused; stale sources require re-verification and re-promotion."}
