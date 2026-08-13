# Benchmark results (Browser Direct-Request) — 2026-08-14

## Environment

- **Host**: Windows 11 / Python 3.11
- **Target**: Local mock HTTP server (`127.0.0.1:9120`) simulating latency
- **Metric**: Complete response cycle time (seconds) measured via Python `time.perf_counter()` over 10 runs.

## Timings

| Run | Baseline (Full JS Simulation) | WarpCache (Direct Bypass) | Speedup |
|---|---|---|---|
| 1 | 0.102315 s | 0.006149 s | 16.64x |
| 2 | 0.101284 s | 0.006167 s | 16.42x |
| 3 | 0.101352 s | 0.005804 s | 17.46x |
| 4 | 0.101680 s | 0.006028 s | 16.87x |
| 5 | 0.101493 s | 0.005803 s | 17.49x |
| 6 | 0.101013 s | 0.005599 s | 18.04x |
| 7 | 0.101213 s | 0.006006 s | 16.85x |
| 8 | 0.101523 s | 0.005578 s | 18.20x |
| 9 | 0.101519 s | 0.006002 s | 16.91x |
| 10 | 0.101026 s | 0.005649 s | 17.88x |
| **Median** | **0.101422 s** | **0.005903 s** | **17.18x** |

## Analysis

- **Baseline Full JS Simulation**: Assumes full headless browser lifecycle (loading web page assets, executing client-side framework hydration, rendering DOM elements). Statically delayed by `100 ms` per call to reflect minimum client rendering overhead.
- **WarpCache Direct Bypass**: Uses the pre-authorized session cookies and token-based signature cache to issue raw HTTP GET requests directly to the target API endpoint, avoiding all browser instrumentation and layout logic. Delayed by `5 ms` representing network/JSON processing delay.
- **Saved Percentage**: **94.18%** time reduction (Median saved: **0.09552 s** per request).

## Conclusion

The direct-request benchmark demonstrates that when a verified execution logic has already been proven and cached via WarpCache (e.g., successful page actions, form configurations), raw API bypass yields a **17.18x speed multiplier**. 

This is a proof-of-concept simulation using local ports under Gemini port-isolation boundaries (`9100-9199`). For safe production adoption, token caching requires strict secret-free auditing as defined in the default activation contract.
