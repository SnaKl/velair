# Fork SnaKl/velair

Fork personnel de [cgonfer/velair](https://github.com/cgonfer/velair). Le domaine reste `velair` :
il remplace le code upstream, il ne s'installe pas à côté.

## Branches

- `main` : miroir strict d'upstream, jamais modifié ici.
- `snakl/room-assist` : les commits du fork, rebasés sur chaque version upstream.

Le code propre au fork vit dans `custom_components/velair/room_assist_fork.py` et
`tests/backend/test_room_assist_fork.py`. Le reste se limite à quelques lignes d'appel, pour
que les rebases restent courts.

## Options ajoutées (par zone, inactives par défaut)

Réglables par WebSocket `velair/update_zone_preconditioning`, pas d'interface graphique.
Elles ne sont écrites dans le stockage que si elles sont activées : tant qu'elles sont à
leur valeur par défaut, les données restent identiques à upstream.

| Option | Défaut | Effet (modes fixes heat / cool, consigne simple) |
|---|---|---|
| `room_sensor_assist_demand_gain` | `1.0` (1.0 à 3.0) | Multiplie l'écart pièce/cible tant que la pièce demande encore du chaud (ou du froid). La correction reste bornée par `room_sensor_assist_max_delta` et par les limites de l'appareil. |
| `room_sensor_assist_directional_limit` | `false` | Chauffage : jamais de consigne sous la cible active. Froid : jamais au-dessus. Diagnostic `directional_limit` = `heating_floor` / `cooling_ceiling`. Demande upstream : cgonfer/velair#91. |

Compromis de la limite directionnelle : Room Assist ne peut plus baisser la consigne pour
freiner un dépassement.

## Suivre upstream

```bash
git fetch upstream --tags
git push origin upstream/main:main
git rebase vX.Y.Z snakl/room-assist
python3 -m unittest discover -s tests
git push --force-with-lease origin snakl/room-assist
```

Si le rebase est en conflit, il ne peut l'être que dans les lignes d'appel de
`scheduler.py`, `models.py` ou `api.py`. Quand upstream livre une de ces options, supprimer
la nôtre plutôt que de garder les deux.
