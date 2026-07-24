# Backend Python/FastAPI, frontend Next.js séparé

Kalenjin a besoin de plus qu'un dashboard de visualisation : un agenda d'entraînements et des vues détaillées de séance façon Runna, avec de l'interactivité riche (Question 13). Un framework de dataviz Python intégré (Streamlit/Dash), envisagé initialement pour sa rapidité de développement en solo, a été écarté car mal adapté à ce type d'UI (agenda, vues détaillées, interactions fines) — ces frameworks sont pensés pour des dashboards de données, pas pour des interfaces applicatives riches.

Le backend est en Python/FastAPI (Question 12), pour rester dans l'écosystème de la librairie Garmin non-officielle (`python-garminconnect`/`garth`) et profiter de la vitesse d'itération de l'utilisateur en Python. Le frontend est une app Next.js séparée qui consomme l'API FastAPI.

Le dashboard de performance (métriques de tendance, récupération, adhérence au plan) vit dans la même app Next.js que l'agenda et le détail des séances, pas dans un outil séparé.
