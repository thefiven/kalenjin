# Kalenjin

Outil personnel de suivi d'entraînement de course à pied (puis multi-sport), qui relie les données Garmin à une analyse IA et génère un plan d'entraînement, avec un tableau de bord de performance et une intégration complète vers Garmin Connect (push des séances vers la montre).

Projet personnel, mono-utilisateur (voir `CONTEXT.md`), pensé pour être compréhensible par n'importe qui qui débarquerait dessus.

## Comprendre le projet

Avant de lire ou modifier le code, commence par :

1. **[`CONTEXT.md`](./CONTEXT.md)** — le glossaire du domaine (vocabulaire, scope, contraintes, design). Source de vérité sur ce que signifient les termes du projet.
2. **[`docs/adr/`](./docs/adr/)** — les décisions d'architecture actées et leur raisonnement (stack, base de données, choix du LLM, politique de conflit Garmin, accès réseau...).
3. **[`docs/agents/`](./docs/agents/)** — comment les agents/skills IA doivent interagir avec ce repo (tracker d'issues, labels de triage, docs de domaine).

## Architecture (cible)

- **Backend** : Python/FastAPI — ingestion Garmin, orchestration IA, génération de plan (ADR-0003)
- **Frontend** : Next.js + shadcn/ui — agenda, détail de séance, dashboard (ADR-0003)
- **Base de données** : PostgreSQL (ADR-0004)
- **LLM** : Gemini (tier gratuit), derrière une interface d'abstraction (ADR-0002)
- **Accès** : VPN uniquement, pas d'authentification applicative (ADR-0005)

Aucune de ces briques n'est encore implémentée — voir les [issues GitHub](https://github.com/thefiven/kalenjin/issues) pour la feuille de route et leur état d'avancement.

## Setup local

_À compléter au fur et à mesure que le backend et le frontend sont scaffoldés (voir issues #1 et #2)._

1. Copier `.env.example` vers `.env` et renseigner les vraies valeurs (jamais commitées — voir `SECURITY.md`).
2. Installer les hooks pre-commit : `pip install pre-commit && pre-commit install`.

## Contribuer

Voir [`CONTRIBUTING.md`](./CONTRIBUTING.md) pour le workflow (branches, commits, PRs) et [`SECURITY.md`](./SECURITY.md) pour la gestion des secrets.

## Licence

Tous droits réservés — voir [`LICENSE`](./LICENSE). Le code est visible publiquement mais non réutilisable sans autorisation.
