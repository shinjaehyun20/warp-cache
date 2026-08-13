# WarpCache default activation contract

## Default gate

WarpCache runs as a **lightweight reuse check** before a nontrivial execution task: research, analysis, design, code/document generation, modification, debugging, validation, file/browser automation, or a multi-step decision.

It does **not** run for simple Q&A, one-shot facts, short explanations, casual brainstorming, arithmetic, or when the user explicitly requests no execution.

The default gate is query-only:

1. Read the existing runtime reuse projection and Golden Set.
2. Return at most five pointer-only candidates.
3. If an `eligible` Golden case exists, load its canonical source and verifier before creating a new temporary script/artifact.
4. If there is no eligible case, or a case is stale, continue immediately with the normal execution contract.

The gate does **not** run a full index refresh, execute a candidate, open a browser, or change a runtime setting by itself.

## Promotion

Only after a repeatable result has a canonical path, input fingerprint, passing verifier and GraphRAG references may it be added to Golden Set. Failed, stale, random temporary, credential-bearing, or user-specific results remain non-reusable.

## Meaningfulness gate

Measure per task category after the first 20 eligible nontrivial tasks. At large corpus scale, bytes avoided and wall-clock saved are first-class outcomes: at a 1 TB decimal corpus, avoiding a 2% unchanged-byte reread is **20 GB** (about **18.63 GiB**) per qualifying refresh.

| Metric | Keep default-on when | Demote to opt-in when |
|---|---|---|
| Reuse hit rate | >= 20% eligible candidate hits | < 10% |
| Verified reuse adoption | >= 3 accepted Golden cases | 0 accepted cases |
| Avoided unchanged I/O | measurable avoided bytes and no safety regression; report absolute GiB + percent | unable to measure after 20 tasks |
| Preparation time | median source/tool discovery improves >= 10% **or** avoided I/O is operationally material | no improvement, no material avoided I/O, or regression >= 5% |
| Safety | 0 stale candidate accepted as current | any stale acceptance |

A category that fails the gate is not marketed as faster and its lookup becomes opt-in until its catalog/GraphRAG coverage improves.

## Evidence fields

Record only: task category, gate result (`eligible|stale|miss`), candidate IDs, whether reused, discovery seconds, verifier outcome, and redacted evidence pointers. Never store source body, credentials, browser session, raw HAR, or request/response body.
