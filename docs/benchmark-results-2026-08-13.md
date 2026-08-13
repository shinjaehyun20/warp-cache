# Benchmark results — 2026-08-13

Environment: Windows 10, Python 3.11.9. Each profile ran five inventory passes; the median excludes no values and reports the complete raw timings in local ignored JSON evidence under `artifacts/`.

| Profile | Baseline median | WarpCache median | Delta | Interpretation |
|---|---:|---:|---:|---|
| 12,000 × 8 KiB (metadata-bound) | 1.497 s | 1.414 s | **5.52% faster** | Small positive result on this host; filesystem metadata and interpreter overhead dominate. |
| 2,000 × 128 KiB (byte-bound) | 0.236 s | 0.237 s | **0.44% slower** | No speed claim; warm OS page cache makes full reads cheap. |

Both profiles re-hashed exactly one file after mutation. The results intentionally demonstrate that digest reuse is a **correctness-preserving optimization with measured, workload-dependent benefit**, not a universal acceleration claim.

## Operational effect not captured by digest timing

Once indexed, assets can be selected via a small reuse brief instead of manually opening/searching every skill/tool/script directory. That reduces discovery and prompt-assembly work, but it is measured separately from file-digest timing.

## Browser lane

No browser/direct-request acceleration claim is included. It needs a user-approved target, paired UI/direct-request measurements, response-equivalence checks, and a secret-free audit trail.
