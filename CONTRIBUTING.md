# Contributing

Thanks for improving WarpCache.

## Before opening a pull request

1. Keep canonical sources canonical; do not add generated caches, local benchmark artifacts, credentials, HAR files, or browser/session data.
2. Add a focused test for behavior changes.
3. Run:

```bash
py -3.11 -m pytest
py -3.11 -m py_compile warp_cache/*.py scripts/*.py
```

4. If performance changes, run both benchmark profiles and report the raw output or a reproducible command. Do not claim a speedup from a single warm-cache run.
5. Golden Set additions must include canonical path, input fingerprint, verifier reference, and GraphRAG references.

## Commit style

Use concise conventional commits such as `feat:`, `fix:`, `docs:`, `test:`, or `perf:`.
