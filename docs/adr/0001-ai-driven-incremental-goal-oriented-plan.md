# Plan d'entraînement piloté par l'IA, orienté objectif, généré incrémentalement

Kalenjin doit remplacer Runna, pas seulement le compléter. On a écarté l'option la plus simple (un éditeur manuel où l'IA ne fait que de l'analyse a posteriori) au profit d'un plan que l'IA construit et ajuste elle-même.

Le plan se structure autour d'un objectif défini par l'utilisateur (distance, date, niveau visé), sur le modèle d'une périodisation classique (Runna/Garmin Coach). Mais contrairement à un plan complet généré d'un coup, seules les séances proches (semaine courante / prochains jours) sont détaillées ; les semaines lointaines restent à gros grain jusqu'à ce qu'on s'en approche. Chaque nouvelle séance réalisée (remontée de Garmin) vient nourrir l'ajustement des séances suivantes déjà détaillées.

Cette approche a été préférée à un plan complet généré à l'avance : réajuster une périodisation entière déjà détaillée à chaque nouvelle donnée est plus lourd et plus fragile (beaucoup de séances jamais réalisées à réécrire) que de ne détailler que ce qui est sur le point d'arriver sur la montre.
