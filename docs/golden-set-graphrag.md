# Golden Set × GraphRAG contract

## Roles

- **GraphRAG / graph index** answers: *what was related to this task?*
- **Golden Set** answers: *which related item is safe to reuse now?*
- **WarpCache** supplies the pointer, revision/hash and reuse decision.

```text
Task intent
  └─ graph traversal → skill / tool / canonical script / verifier / artifact
                         └─ Golden Set gate → eligible | stale_source
                                                  └─ native runtime executes or repairs
```

## Promotion gate

A case is promoted only with all of:

1. a canonical regular-file path (never a random temp path);
2. source SHA-256;
3. input fingerprint (source/data/config version identity);
4. verifier reference that passed for that case;
5. one or more graph references (`task:*`, `tool:*`, `artifact:*`, etc.);
6. a concise reuse summary.

Temporary scripts are therefore not reused just because they exist. A repeated success is first moved or rewritten into a canonical project/script lane, verified, then promoted.

## Reuse gate

At lookup, WarpCache recomputes the canonical source SHA-256:

- hash matches → `eligible`: may be passed to the owning runtime as a candidate;
- hash differs/missing → `stale_source`: must be re-verified and re-promoted;
- no graph/Golden record → create new work under the normal project boundary.

No source body, credential, browser session, request body or response body is copied into the Golden Set.
