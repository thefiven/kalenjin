# Security

Kalenjin is an invite-only, multi-tenant SaaS (see `CONTEXT.md`), but it's operated solo and handles real credentials and personal health data. Treat these rules as non-negotiable even though it's a solo-operated project.

## Secrets

- **Never commit real credentials.** Garmin login, Gemini API key, database URL, and any future secret live in a local `.env` file (gitignored) or the deployment platform's secret store — never hardcoded, never in a config file that gets committed.
- `.env.example` at the repo root lists every required environment variable with a placeholder value. Keep it in sync whenever a new secret is introduced.
- The pre-commit hooks include secret scanning (`gitleaks`) — if it flags a commit, do not bypass it without understanding why first.
- If a secret is ever committed by mistake: rotate it immediately (Garmin password, Gemini key, etc.) — removing it from a later commit does not remove it from git history.
- Per-user secrets (Garmin credentials, Gemini API key) are encrypted at rest at the application level before being written to Postgres, with the encryption key held separately in a k3s Secret (ADR-0010) — never store or log these in plaintext.

## Access control

- Per ADR-0008, login is via Google OAuth ("Sign in with Google"), gated by an invite allowlist checked before an account is created — there's no application password to manage. Do not add a new authentication method without keeping the invite allowlist as the gate.

## Reporting

Solo project, no external reporting process today. If this ever opens up to other contributors, add a disclosure email here before accepting outside contributions.
