# Kalenjin

Outil personnel de suivi d'entraînement de course à pied (puis multi-sport), qui relie les données Garmin à une analyse IA et génère un plan d'entraînement, avec un tableau de bord de performance et une intégration complète vers Garmin Connect (push des séances vers la montre).

SaaS multi-utilisateur en invite-only (voir `CONTEXT.md`), pensé pour être compréhensible par n'importe qui qui débarquerait dessus.

## Comprendre le projet

Avant de lire ou modifier le code, commence par :

1. **[`CONTEXT.md`](./CONTEXT.md)** — le glossaire du domaine (vocabulaire, scope, contraintes, design). Source de vérité sur ce que signifient les termes du projet.
2. **[`docs/adr/`](./docs/adr/)** — les décisions d'architecture actées et leur raisonnement (stack, base de données, choix du LLM, politique de conflit Garmin, authentification...).
3. **[`docs/agents/`](./docs/agents/)** — comment les agents/skills IA doivent interagir avec ce repo (tracker d'issues, labels de triage, docs de domaine).

## Architecture

- **Backend** : Python/FastAPI — ingestion Garmin, orchestration IA, génération de plan (ADR-0003)
- **Frontend** : Next.js + shadcn/ui — agenda, détail de séance, dashboard (ADR-0003)
- **Base de données** : PostgreSQL (ADR-0004)
- **LLM** : Gemini (tier gratuit), derrière une interface d'abstraction (ADR-0002)
- **Accès** : Google OAuth ("Sign in with Google") avec liste d'invitation, pas de mot de passe applicatif (ADR-0008)

Voir les [issues GitHub](https://github.com/thefiven/kalenjin/issues) pour la feuille de route et l'état d'avancement des fonctionnalités.

## Setup local

1. Copier `.env.example` vers `.env` et renseigner les vraies valeurs (jamais commitées — voir `SECURITY.md`).
2. Installer les hooks pre-commit : `pip install pre-commit && pre-commit install`.
3. Lancer PostgreSQL : `docker-compose up -d postgres`.
4. Backend (`backend/`) : `pip install -e .[dev]`, puis `alembic upgrade head` pour appliquer les migrations, puis `uvicorn kalenjin.api:app --reload` pour démarrer l'API.
5. Frontend (`frontend/`) : `npm install`, puis `npm run dev`.

## Contribuer

Voir [`CONTRIBUTING.md`](./CONTRIBUTING.md) pour le workflow (branches, commits, PRs) et [`SECURITY.md`](./SECURITY.md) pour la gestion des secrets.

## Licence

Tous droits réservés — voir [`LICENSE`](./LICENSE). Le code est visible publiquement mais non réutilisable sans autorisation.
