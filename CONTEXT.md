# Kalenjin

Outil personnel de suivi d'entraînement de course à pied (puis multi-sport), qui relie les données Garmin à une analyse IA et à un tableau de bord de performance.

## Language

**Sport**:
Une discipline pratiquée (ex: course à pied, vélo). Kalenjin gère plusieurs sports à plat — chaque séance appartient à un seul sport ; il n'y a pas de séance composite mêlant plusieurs sports (pas de "brick workout").
_Avoid_: Discipline, activité (quand le sens visé est le sport lui-même, pas l'occurrence).

**Objectif**:
Une cible que l'utilisateur définit (distance, date, niveau visé), qui sert de cadre de périodisation pour générer le plan d'entraînement.
_Avoid_: But, cible (quand il s'agit de cette entité précise, pas d'usage général).

**Plan**:
La suite de séances menant à un objectif. Généré et ajusté par l'IA de manière incrémentale : seules les séances proches sont détaillées, les semaines lointaines restent à gros grain jusqu'à ce qu'on s'en approche.
_Avoid_: Programme, périodisation (la périodisation est le principe, le Plan est l'instance concrète pour un Objectif donné).

**Séance**:
Une session d'entraînement prévue ou réalisée, rattachée à un Sport et (si prévue) à un Plan. Kalenjin en est la source de vérité : toute modification manuelle faite depuis Garmin Connect ou la montre est écrasée à la prochaine synchro.
_Avoid_: Entraînement, workout, activité (réserver "activité" à la donnée brute remontée par Garmin après réalisation).

**Rapport**:
L'analyse générée par l'IA après une Séance réalisée (ce qui est bien, axes d'amélioration). Sert de matière première aux Synthèses périodiques et au futur mode conversationnel.
_Avoid_: Feedback, retour (termes utilisés de façon informelle en dehors du glossaire).

## Contraintes

- Préférence générale pour l'open source (librairies, frameworks, LLM). Une exception assumée existe pour l'instant : Gemini (propriétaire) est utilisé comme LLM par pragmatisme, voir ADR-0002.

## Design

Thème visuel neutre et épuré (type Linear/Notion) avec un unique accent de couleur, plutôt qu'une identité sportive marquée — la donnée (graphiques, agenda) porte l'identité visuelle, pas le chrome de l'UI. Composants : shadcn/ui sur Next.js/Tailwind, thème clair/sombre natif.

## Scope

- Usage strictement personnel (un seul utilisateur, un seul compte Garmin). Pas de multi-tenant pour l'instant.
- Connexion Garmin via `python-garminconnect` (v0.3.5+), librairie communautaire non-officielle authentifiée avec les identifiants Garmin de l'utilisateur — pas l'API officielle Garmin Health/Connect Developer Program. `garth`, dont dépendait l'auth historique, est déprécié depuis que Garmin a cassé son flow d'auth (mars 2026) ; `python-garminconnect` a survécu en réécrivant son auth avec `curl_cffi` (impersonation TLS). Ni Strava (pas de push de séance vers une montre) ni Health Connect (entrepôt local au téléphone, pas d'API cloud) ne peuvent se substituer à Garmin Connect pour ce projet, car le push de séances structurées vers la montre est irremplaçable par ces alternatives.
