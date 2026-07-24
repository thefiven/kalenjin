# Security

Kalenjin is a personal, single-user project (see `CONTEXT.md`), but it handles real credentials and personal health data. Treat these rules as non-negotiable even though it's a solo project — see ADR-0005.

## Secrets

- **Never commit real credentials.** Garmin login, Gemini API key, database URL, and any future secret live in a local `.env` file (gitignored) or the deployment platform's secret store — never hardcoded, never in a config file that gets committed.
- `.env.example` at the repo root lists every required environment variable with a placeholder value. Keep it in sync whenever a new secret is introduced.
- The pre-commit hooks include secret scanning (`gitleaks`) — if it flags a commit, do not bypass it without understanding why first.
- If a secret is ever committed by mistake: rotate it immediately (Garmin password, Gemini key, etc.) — removing it from a later commit does not remove it from git history.

## Access control

- Per ADR-0005, the app has no application-level login. Access is restricted entirely at the network layer via VPN (Tailscale). Do not add a public-facing deployment without also adding real authentication first — the "no auth" decision is only safe because of the VPN boundary.

## Reporting

Solo project, no external reporting process today. If this ever opens up to other contributors, add a disclosure email here before accepting outside contributions.
