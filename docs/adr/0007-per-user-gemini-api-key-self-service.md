# Chaque utilisateur fournit sa propre clé API Gemini

Passer d'une clé Gemini unique partagée (ADR-0002) à une clé API Gemini par utilisateur, saisie une fois via un écran d'onboarding self-service (même schéma que la connexion Garmin, ADR-0006), plutôt qu'une clé unique côté opérateur. L'objectif n'est pas la volumétrie — le tier gratuit suffit largement à l'usage invite-only actuel — mais l'isolation de quota : un utilisateur qui régénère beaucoup son plan ne doit pas épuiser le quota gratuit des autres.

Une intégration OAuth (réutiliser le login Google de l'utilisateur pour appeler Gemini en son nom, sans clé séparée) a été écartée : le tier gratuit est une propriété des clés API Google AI Studio, pas de l'accès Vertex AI par jeton OAuth — il n'y a donc pas moyen d'obtenir un quota gratuit isolé par utilisateur sans que chacun détienne sa propre clé.
