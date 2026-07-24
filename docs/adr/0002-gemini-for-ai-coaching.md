# Gemini comme LLM pour l'analyse et la génération de plan

Kalenjin utilise un LLM généraliste avec un contexte spécialisé "coach de course à pied" (Question 11 de la session de grilling) plutôt qu'un service de coaching sportif dédié. On a choisi Gemini (plan gratuit de Google AI Studio) plutôt que Claude comme fournisseur, alors que le reste du développement du projet se fait avec Claude Code.

Cette décision n'est pas motivée par la qualité du modèle, mais par une contrainte invisible dans le code : les tokens Claude de l'utilisateur sont réservés au développement (Claude Code), et le tier gratuit de Gemini a des quotas confortables pour le faible volume d'appels que Kalenjin génère (analyse post-séance + ajustements de plan occasionnels).

Le choix reste réversible : l'appel au LLM doit passer par une interface d'abstraction générique (pas d'appel direct au SDK Gemini disséminé dans le code), pour permettre de changer de fournisseur plus tard sans réécriture majeure.

Ce choix est en tension avec une préférence générale du projet pour l'open source : Gemini est un modèle propriétaire. Gemini est retenu pour l'instant par pragmatisme (gratuit, aucune infra à gérer), mais un modèle open source auto-hébergé (ex: via Ollama) est une évolution envisagée une fois le homelab k3s en place — l'abstraction LLM ci-dessus existe aussi pour rendre cette bascule possible sans réécriture majeure.
