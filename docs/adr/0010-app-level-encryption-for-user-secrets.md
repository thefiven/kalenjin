# Chiffrement applicatif pour les secrets utilisateur (mot de passe Garmin, clé Gemini)

Les identifiants Garmin (ADR-0006) et la clé API Gemini (ADR-0007) stockés par utilisateur sont chiffrés au niveau applicatif (AES-GCM/Fernet) avant écriture en base, avec la clé de chiffrement elle-même stockée dans un Secret k3s — séparée de la base Postgres qui contient le texte chiffré.

Un gestionnaire de secrets externe (Vault auto-hébergé, KMS cloud) a été écarté : pour un projet invite-only opéré par une seule personne, faire tourner et opérer ce service en plus est disproportionné par rapport au gain (rotation, audit log) face au risque réellement visé — une fuite du dump Postgres seul, déjà couverte par la séparation clé/DB.
