# Pas d'authentification applicative, accès restreint par VPN

Kalenjin n'implémente aucun système de login/mot de passe. L'accès est protégé exclusivement au niveau réseau, via un VPN (Tailscale), même si l'app est déployée sur un VPS/k3s potentiellement joignable publiquement.

C'est un choix délibéré cohérent avec le scope strictement mono-utilisateur (Question 1) : pour un seul utilisateur, gérer sessions, hash de mots de passe et réinitialisation est un coût de développement et une surface d'attaque supplémentaires pour un problème déjà résolu par la restriction réseau. Si seul le VPN peut atteindre l'app, aucune authentification applicative n'est nécessaire.

Si le projet devait un jour s'ouvrir à plusieurs utilisateurs, cette décision serait à revoir en priorité.
