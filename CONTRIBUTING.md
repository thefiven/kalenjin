# Contributing

Projet personnel, mais avec des conventions strictes pour que le code reste clair même après des mois sans y toucher.

## Workflow

- **Pas de push direct sur `main`** — la branche est protégée (voir la config du repo). Toute modification passe par une Pull Request, même pour un changement solo.
- **Branches** : `<type>/<slug-court>`, ex. `feat/garmin-ingestion`, `fix/incremental-sync-duplicate`.
- **Commits** : format [Conventional Commits](https://www.conventionalcommits.org/) — `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `test:`. Message court à l'impératif, le "pourquoi" plutôt que le "quoi" si ce n'est pas évident.
- **Pull Requests** : utilisent le template `.github/pull_request_template.md`. La CI (hooks pre-commit) doit passer avant de merger.

## Avant de coder

- Lis `CONTEXT.md` pour le vocabulaire du domaine — n'invente pas de synonyme pour un terme déjà défini.
- Regarde `docs/adr/` pour les décisions déjà prises dans la zone que tu modifies. Si ton changement contredit un ADR existant, dis-le explicitement dans la PR plutôt que de passer outre en silence.

## Quand créer un ADR

Seulement si les trois conditions sont réunies : difficile à revenir en arrière, surprenant sans contexte, résultat d'un vrai arbitrage. Voir le format dans les ADR existants (`docs/adr/000N-*.md`) — un ADR peut être un seul paragraphe.

## Quand mettre à jour CONTEXT.md

Dès qu'un terme du domaine est défini ou clarifié — pas de batch, on le fait au moment où la décision est prise (voir le skill `domain-modeling`). `CONTEXT.md` est un glossaire, jamais un cahier des charges ni un scratch pad d'implémentation.

## Qualité et sécurité

- Installer les hooks : `pip install pre-commit && pre-commit install`. Ils tournent aussi en CI (`.github/workflows/ci.yml`), donc les contourner en local ne suffit pas à passer une PR.
- Ne jamais committer de secret — voir `SECURITY.md`. `.env.example` documente les variables attendues.
- Toute nouvelle brique de code (backend ou frontend) doit arriver avec ses propres tests et, si elle introduit un nouvel écosystème de lint (ruff, eslint...), un job CI dédié ajouté à `.github/workflows/ci.yml`.
