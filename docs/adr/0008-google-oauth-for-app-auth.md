# OAuth2 Google pour l'authentification applicative

Kalenjin passe multi-tenant (invite-only) : la protection réseau seule (ADR-0005) ne suffit plus dès qu'il faut distinguer les utilisateurs entre eux. On authentifie via Google OAuth ("Sign in with Google") plutôt que mot de passe, magic link, ou simple jeton d'invitation : ça évite de construire la gestion de mots de passe (hash, réinitialisation, envoi d'email transactionnel), et le cercle invite-only actuel a quasi certainement tous un compte Google.

Ce choix crée une dépendance forte à Google pour le login (écran de consentement OAuth, disponibilité du service), jugée acceptable pour un usage non commercial et invite-only. D'autres moyens d'authentification pourront être ajoutés plus tard si le besoin apparaît (ouverture au public, invités sans compte Google) — ce n'est pas exclusif par construction, juste le seul moyen implémenté pour l'instant.
