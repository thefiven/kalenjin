# PostgreSQL comme base de données

Kalenjin stocke les séances, plans, objectifs et retours IA dans PostgreSQL plutôt que SQLite. SQLite aurait suffi pour un usage strictement mono-utilisateur (Question 1), mais Postgres est cohérent avec l'intention de déployer sur k3s/Kubernetes (Question 4, un Postgres conteneurisé avec volume persistant est un pattern standard) et avec le besoin de requêtes analytiques pour les tendances du dashboard (Question 9), sans surcoût réel une fois conteneurisé.
