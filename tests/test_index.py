from pathlib import Path

from warp_cache import WarpIndex


def test_unchanged_file_reuses_digest(tmp_path: Path) -> None:
    source = tmp_path / "asset.txt"
    source.write_text("stable", encoding="utf-8")
    index = WarpIndex()
    first = index.fingerprint(source)
    second = index.fingerprint(source)
    assert first.sha256 == second.sha256
    assert index.hashes_computed == 1
    assert index.hashes_reused == 1


def test_changed_file_invalidates_cached_digest(tmp_path: Path) -> None:
    source = tmp_path / "asset.txt"
    source.write_text("before", encoding="utf-8")
    index = WarpIndex()
    before = index.fingerprint(source)
    source.write_text("after-longer", encoding="utf-8")
    after = index.fingerprint(source)
    assert before.sha256 != after.sha256
    assert index.hashes_computed == 2
