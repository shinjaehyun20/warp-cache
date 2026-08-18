import json
from pathlib import Path
import subprocess
import sys

import pytest

from warp_cache.golden_set import GoldenCase
from warp_cache.har_contract import HarContractError, derive_endpoint_contract, validate_endpoint_contract_file


SECRET = "super-secret-cookie-value"


def sample_har() -> dict:
    return {
        "log": {
            "entries": [
                {
                    "_resourceType": "fetch",
                    "request": {
                        "method": "POST",
                        "url": "https://api.example.test/v1/orders/12345?limit=20&access_token=never-store",
                        "headers": [
                            {"name": "Accept", "value": "application/json"},
                            {"name": "Cookie", "value": SECRET},
                            {"name": "Authorization", "value": "Bearer never-store"},
                        ],
                        "postData": {"mimeType": "application/json", "text": '{"customer":"Ada","password":"never-store","items":[{"sku":"x","count":2}]}'},
                    },
                    "response": {"status": 200, "content": {"mimeType": "application/json", "text": '{"email":"ada@example.test","payment_token":"never-store"}'}},
                },
                {
                    "_resourceType": "image",
                    "request": {"method": "GET", "url": "https://api.example.test/logo.png", "headers": []},
                    "response": {"status": 200, "content": {"mimeType": "image/png", "text": "binary"}},
                },
            ]
        }
    }


def test_derivation_keeps_endpoint_shape_and_drops_secret_values() -> None:
    contract = derive_endpoint_contract(sample_har())
    assert contract["raw_content_persisted"] is False
    assert contract["endpoint_count"] == 1
    endpoint = contract["endpoints"][0]
    assert endpoint["path_template"] == "/v1/orders/{id}"
    assert endpoint["query_parameters"] == ["limit"]
    assert endpoint["cookie_required"] is True
    assert endpoint["authorization_required"] is True
    assert endpoint["request_body"]["shape"] == {"customer": "string", "items": {"array_of": {"count": "number", "sku": "string"}}}
    rendered = json.dumps(contract, sort_keys=True)
    for forbidden in (SECRET, "never-store", "ada@example.test", "Bearer"):
        assert forbidden not in rendered


def test_raw_har_and_non_contract_json_cannot_be_promoted(tmp_path: Path) -> None:
    raw_har = tmp_path / "capture.har"
    raw_har.write_text(json.dumps(sample_har()), encoding="utf-8")
    with pytest.raises(ValueError, match="raw HAR"):
        GoldenCase.promote(kind="artifact", canonical_path=raw_har, input_fingerprint="x", verifier_ref="pytest", graph_refs=["capability:network"], summary="must fail")
    disguised = tmp_path / "capture.json"
    disguised.write_text(json.dumps(sample_har()), encoding="utf-8")
    with pytest.raises(ValueError, match="raw HAR"):
        GoldenCase.promote(kind="artifact", canonical_path=disguised, input_fingerprint="x", verifier_ref="pytest", graph_refs=["capability:network"], summary="must fail")


def test_safe_contract_can_be_promoted_but_tampering_is_rejected(tmp_path: Path) -> None:
    contract_path = tmp_path / "endpoint-contract.json"
    contract_path.write_text(json.dumps(derive_endpoint_contract(sample_har())), encoding="utf-8")
    validate_endpoint_contract_file(contract_path)
    case = GoldenCase.promote(kind="endpoint_contract", canonical_path=contract_path, input_fingerprint="shape:v1", verifier_ref="pytest:tests/test_har_contract.py", graph_refs=["capability:authorized-network-recipe"], summary="safe endpoint contract")
    assert case.kind == "endpoint_contract"
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    payload["endpoints"][0]["request_header_names"].append("x-api-key")
    contract_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(HarContractError, match="sensitive header"):
        validate_endpoint_contract_file(contract_path)


def test_cli_writes_only_safe_contract(tmp_path: Path) -> None:
    raw_har = tmp_path / "input.har"
    output = tmp_path / "safe-contract.json"
    raw_har.write_text(json.dumps(sample_har()), encoding="utf-8")
    run = subprocess.run(
        [sys.executable, "scripts/warp_cache.py", "har-derive-contract", "--input", str(raw_har), "--output", str(output)],
        cwd=Path(__file__).parents[1], text=True, capture_output=True, check=True,
    )
    assert '"raw_content_persisted": false' in run.stdout
    rendered = output.read_text(encoding="utf-8")
    assert SECRET not in rendered
    assert "never-store" not in rendered