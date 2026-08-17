from pathlib import Path
from typing import cast

import pytest

from warp_cache.golden_set import GoldenCase, GoldenSet


def test_verified_case_is_reusable_and_mutation_demotes_it(tmp_path: Path) -> None:
    script = tmp_path / "canonical" / "build_report.py"
    script.parent.mkdir()
    script.write_text("print('v1')", encoding="utf-8")
    registry = GoldenSet(tmp_path / "golden-set.json")
    case = GoldenCase.promote(
        kind="script", canonical_path=script, input_fingerprint="source-pack:v1",
        verifier_ref="tests/test_report.py::test_build", graph_refs=["task:weekly-report", "tool:python"],
        summary="verified weekly report builder script",
    )
    registry.promote(case)
    assert registry.reuse_candidates("weekly report")["candidates"][0]["reuse_state"] == "eligible"
    script.write_text("print('v2')", encoding="utf-8")
    assert registry.reuse_candidates("weekly report")["candidates"][0]["reuse_state"] == "stale_source"


def test_promotion_rejects_non_list_graph_references(tmp_path: Path) -> None:
    script = tmp_path / "canonical.py"
    script.write_text("print('verified')", encoding="utf-8")

    with pytest.raises(ValueError, match="graph reference"):
        GoldenCase.promote(
            kind="script", canonical_path=script, input_fingerprint="input:v1",
            verifier_ref="tests/test_canonical.py", graph_refs=cast(list[str], "task:report"), summary="verified script",
        )


@pytest.mark.parametrize("limit", [0, -1, 21, True])
def test_query_rejects_invalid_limits(tmp_path: Path, limit: int) -> None:
    with pytest.raises(ValueError, match="limit must be an integer"):
        GoldenSet(tmp_path / "golden-set.json").reuse_candidates("weekly report", limit=limit)
