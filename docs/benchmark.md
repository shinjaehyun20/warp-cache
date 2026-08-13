# Benchmark contract

## What is measured

`python scripts/benchmark.py` creates a deterministic temporary corpus, then measures two identical inventory passes. Use at least two profiles before making a product claim:

- metadata-bound: `--files 12000 --bytes-per-file 8192`
- byte-bound: `--files 2000 --bytes-per-file 131072`

1. **Baseline** — computes SHA-256 for every regular source every run.
2. **WarpCache** — first run computes SHA-256; later unchanged runs reuse the digest only when `(resolved path, size, mtime_ns)` is identical.

The report includes all runs, median, p95, savings, speed multiplier, corpus byte count, interpreter and platform. A changed-file check proves that a modified source invalidates the cached digest. A negative result is valid evidence: do not claim acceleration for a metadata-bound corpus if it is slower.

## What is not claimed

- It does not claim arbitrary Python business logic is faster.
- It does not claim UI/browser work is faster without a paired authorized endpoint experiment.
- It does not cache or replay credentials, cookies, request bodies, or response bodies.

## Browser Network lane

The browser lane is intentionally separate. A valid experiment needs:

- explicit user-approved origin and data scope;
- same authenticated browser session for the baseline;
- UI-flow vs direct-request p50/p95 and success-rate measurements;
- response schema/equivalence verifier;
- expiry/error/fallback-browser behavior;
- secret-free audit output only.

Without those controls, the status is **unproven**, not accelerated.
