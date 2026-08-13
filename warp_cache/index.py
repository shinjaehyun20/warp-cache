from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DigestRecord:
    path: str
    size: int
    mtime_ns: int
    sha256: str


class WarpIndex:
    """A disposable digest projection keyed by file identity metadata.

    Reuse is permitted only when path, byte size and nanosecond mtime match.
    A source mutation therefore falls back to a new SHA-256 calculation.
    """

    def __init__(self) -> None:
        self._records: dict[str, DigestRecord] = {}
        self.hashes_computed = 0
        self.hashes_reused = 0

    @staticmethod
    def _digest(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def fingerprint(self, source: str | Path) -> DigestRecord:
        path = Path(source).resolve()
        stat = path.stat()
        key = str(path)
        cached = self._records.get(key)
        if cached and cached.size == stat.st_size and cached.mtime_ns == stat.st_mtime_ns:
            self.hashes_reused += 1
            return cached
        record = DigestRecord(key, stat.st_size, stat.st_mtime_ns, self._digest(path))
        self._records[key] = record
        self.hashes_computed += 1
        return record

    def refresh(self, sources: list[str | Path]) -> list[DigestRecord]:
        return [self.fingerprint(source) for source in sources]
