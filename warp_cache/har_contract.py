from __future__ import annotations

"""Derive a secret-free endpoint contract from a local HAR without retaining it."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

SCHEMA = "warp-cache-endpoint-contract/v1"
SENSITIVE_NAME = re.compile(r"(?:authorization|cookie|token|secret|password|api[-_]?key|session|set-cookie)", re.I)
ID_SEGMENT = re.compile(r"^(?:\d+|[0-9a-f]{8}-[0-9a-f-]{27,}|[0-9a-f]{16,})$", re.I)


class HarContractError(ValueError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_name(value: str) -> bool:
    return bool(value) and not SENSITIVE_NAME.search(value)


def _path_template(path: str) -> str:
    return "/".join("{id}" if ID_SEGMENT.fullmatch(part) else part for part in path.split("/")) or "/"


def _json_shape(value: Any, *, depth: int = 0) -> Any:
    """Keep only JSON field names and types—never values."""
    if depth >= 4:
        return "truncated"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return {"array_of": _json_shape(value[0], depth=depth + 1) if value else "unknown"}
    if isinstance(value, dict):
        return {
            key: _json_shape(child, depth=depth + 1)
            for key, child in sorted(value.items())
            if _safe_name(str(key))
        }
    return type(value).__name__


def _entry_is_api(entry: dict[str, Any]) -> bool:
    resource = str(entry.get("_resourceType", "")).casefold()
    mime = str(entry.get("response", {}).get("content", {}).get("mimeType", "")).casefold()
    return resource in {"xhr", "fetch"} or "json" in mime


def _headers(entry: dict[str, Any]) -> tuple[list[str], bool, bool]:
    names: list[str] = []
    cookie = auth = False
    for header in entry.get("request", {}).get("headers", []):
        if not isinstance(header, dict):
            continue
        name = str(header.get("name", "")).strip().casefold()
        if not name:
            continue
        cookie = cookie or name == "cookie"
        auth = auth or bool(SENSITIVE_NAME.search(name))
        if _safe_name(name):
            names.append(name)
    return sorted(set(names)), cookie, auth


def _request_shape(entry: dict[str, Any]) -> dict[str, Any] | None:
    post = entry.get("request", {}).get("postData", {})
    if not isinstance(post, dict) or not post.get("text"):
        return None
    content_type = str(post.get("mimeType", "")).split(";", 1)[0].strip().casefold()
    result: dict[str, Any] = {"content_type": content_type or "unknown", "observed": True}
    if "json" not in content_type:
        result["shape"] = "unparsed"
        return result
    try:
        result["shape"] = _json_shape(json.loads(str(post["text"])))
    except (TypeError, ValueError, json.JSONDecodeError):
        result["shape"] = "unparsed"
    return result


def derive_endpoint_contract(har: dict[str, Any]) -> dict[str, Any]:
    entries = har.get("log", {}).get("entries")
    if not isinstance(entries, list):
        raise HarContractError("HAR must contain log.entries")
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    omitted_sensitive_params = 0
    for entry in entries:
        if not isinstance(entry, dict) or not _entry_is_api(entry):
            continue
        request = entry.get("request", {})
        if not isinstance(request, dict):
            continue
        method = str(request.get("method", "")).upper()
        url = urlsplit(str(request.get("url", "")))
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"} or url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            continue
        key = (method, url.hostname.casefold(), _path_template(url.path))
        record = grouped.setdefault(key, {
            "method": method, "host": url.hostname.casefold(), "path_template": _path_template(url.path),
            "query_parameters": set(), "request_header_names": set(), "cookie_required": False,
            "authorization_required": False, "request_body": None, "response_content_types": set(),
            "response_statuses": set(), "observations": 0,
        })
        record["observations"] += 1
        for name, _value in parse_qsl(url.query, keep_blank_values=True):
            if _safe_name(name):
                record["query_parameters"].add(name)
            else:
                omitted_sensitive_params += 1
        header_names, cookie, auth = _headers(entry)
        record["request_header_names"].update(header_names)
        record["cookie_required"] = record["cookie_required"] or cookie
        record["authorization_required"] = record["authorization_required"] or auth
        shape = _request_shape(entry)
        if shape is not None and record["request_body"] is None:
            record["request_body"] = shape
        response = entry.get("response", {})
        if isinstance(response, dict):
            status = response.get("status")
            if isinstance(status, int):
                record["response_statuses"].add(status)
            content = response.get("content", {})
            if isinstance(content, dict):
                mime = str(content.get("mimeType", "")).split(";", 1)[0].strip().casefold()
                if mime:
                    record["response_content_types"].add(mime)
    endpoints = []
    for key in sorted(grouped):
        record = grouped[key]
        endpoints.append({
            "method": record["method"], "host": record["host"], "path_template": record["path_template"],
            "query_parameters": sorted(record["query_parameters"]),
            "request_header_names": sorted(record["request_header_names"]),
            "cookie_required": record["cookie_required"], "authorization_required": record["authorization_required"],
            "request_body": record["request_body"], "response_content_types": sorted(record["response_content_types"]),
            "response_statuses": sorted(record["response_statuses"]), "observations": record["observations"],
        })
    return {
        "schema": SCHEMA,
        "generated_at": _now_iso(),
        "raw_content_persisted": False,
        "sensitive_query_parameters_omitted": omitted_sensitive_params,
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
    }


def derive_endpoint_contract_file(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    source = Path(input_path)
    target = Path(output_path)
    if source.resolve() == target.resolve():
        raise HarContractError("input HAR and output contract must be different files")
    try:
        har = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarContractError(f"unable to read HAR: {exc}") from exc
    contract = derive_endpoint_contract(har)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return contract


def is_raw_har_payload(value: Any) -> bool:
    return isinstance(value, dict) and isinstance(value.get("log"), dict) and isinstance(value["log"].get("entries"), list)


def validate_endpoint_contract_file(path: str | Path) -> None:
    source = Path(path)
    if source.suffix.casefold() == ".har":
        raise HarContractError("raw HAR files cannot be promoted")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarContractError(f"endpoint contract must be readable JSON: {exc}") from exc
    if is_raw_har_payload(payload):
        raise HarContractError("raw HAR payloads cannot be promoted")
    required = {"schema", "generated_at", "raw_content_persisted", "sensitive_query_parameters_omitted", "endpoint_count", "endpoints"}
    if not isinstance(payload, dict) or set(payload) != required or payload.get("schema") != SCHEMA:
        raise HarContractError("invalid endpoint contract schema")
    if payload.get("raw_content_persisted") is not False or not isinstance(payload.get("endpoints"), list):
        raise HarContractError("endpoint contract must declare raw_content_persisted=false")
    if payload.get("endpoint_count") != len(payload["endpoints"]):
        raise HarContractError("endpoint_count does not match endpoints")
    serialized = json.dumps(payload, ensure_ascii=False).casefold()
    if any(token in serialized for token in ('"authorization"', '"cookie"', '"set-cookie"', '"x-api-key"')):
        raise HarContractError("endpoint contract contains a sensitive header name")