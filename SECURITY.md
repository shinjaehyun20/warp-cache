# Security policy

## Supported versions

Security fixes are applied to the latest `main` revision.

## Reporting a vulnerability

Please **do not** open a public issue for a suspected vulnerability.

Use GitHub's private security advisory flow for this repository, or contact the maintainer through GitHub with a minimal reproduction. Include affected revision, impact, and safe reproduction steps. Do not include tokens, cookies, HAR files, raw request/response bodies, or personal data.

## Design boundary

WarpCache is intended to store pointer-only, regenerable metadata. Credentials, browser sessions, authorization headers, raw HAR, request bodies, and response bodies must never be committed or promoted into a Golden Set.
