# Safe network recipes

WarpCache can derive a reusable **endpoint contract** from a HAR, but a HAR is
only an ephemeral local input. It is never a cache record, Golden Set source,
GraphRAG payload, Git artifact, or cross-runtime handoff.

## Flow

```text
authorized browser interaction
  -> local HAR (ephemeral, sensitive)
  -> har-derive-contract
  -> secret-free endpoint contract
  -> fresh verifier
  -> Golden Set endpoint_contract (optional)
```

`har-derive-contract` emits only method, host, path template, non-sensitive
parameter/header **names**, boolean auth/cookie requirements, JSON field/type
shape, response status/content-type, and observation count. It never emits
header values, query values, request values, or response bodies.

```bash
py -3.11 scripts/warp_cache.py har-derive-contract \
  --input C:/safe-local/temporary-capture.har \
  --output artifacts/example-endpoint-contract.json
```

The input is read-only. Delete or store that HAR through the owning browser or
security workflow after derivation; WarpCache deliberately does not automate
credential-bearing cleanup.

## Promotion boundary

Only the derived JSON contract may be promoted, and only after a fresh
authorized replay verifier has passed:

```bash
py -3.11 scripts/warp_cache.py golden-promote \
  --kind endpoint_contract \
  --canonical-path artifacts/example-endpoint-contract.json \
  --input-fingerprint "site-contract:v1" \
  --verifier-ref "owner-run:authorized-replay:PASS" \
  --graph-ref "capability:authorized-network-recipe" \
  --summary "Verified secret-free endpoint contract"
```

The Golden gate rejects `.har` files and HAR-shaped JSON, including a HAR
renamed to `.json`. An endpoint contract that advertises a sensitive header
name is also rejected.

## Runtime handoff

Hermes, Codex, Claude, Antigravity/Gemini, and Copilot may consume the same
contract as a **pointer-only capability description**. Each runtime must keep
credentials in its own authorized secret/session surface, implement its own
HTTP adapter, and run its own verifier. No cookie, authorization value, client
code carrying a secret, or raw HAR crosses runtime boundaries.

## Non-goals

- bypassing authentication, CAPTCHAs, bot detection, or rate limits;
- replaying an endpoint without the site's required authorization;
- retaining a raw HAR or deriving a persistent cookie/token store;
- treating an endpoint shape as a production-ready API client without a fresh
  owner-authorized response-equivalence check.