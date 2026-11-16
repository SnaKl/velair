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

Réglables dans le panneau Velair, écran Room Assist de chaque zone, bloc « Options du fork »
(`frontend/src/velair/views/room-assist-fork-view.ts`), ou par WebSocket
`velair/update_zone_preconditioning`.
Elles ne sont écrites dans le stockage que si elles sont activées : tant qu'elles sont à
leur valeur par défaut, les données restent identiques à upstream.

| Option | Défaut | Effet (modes fixes heat / cool, consigne simple) |
|---|---|---|
| `room_sensor_assist_demand_gain` | `1.0` (1.0 à 3.0) | Multiplie l'écart pièce/cible tant que la pièce demande encore du chaud (ou du froid). La correction reste bornée par `room_sensor_assist_max_delta` et par les limites de l'appareil. |
| `room_sensor_assist_directional_limit` | `false` | Chauffage : jamais de consigne sous la cible active. Froid : jamais au-dessus. Diagnostic `directional_limit` = `heating_floor` / `cooling_ceiling`. Demande upstream : cgonfer/velair#91. |
| `room_sensor_assist_demand_fan_mode` | absent | Mode de ventilation de rattrapage (ex. `high`). Appliqué quand la pièce est à `room_sensor_assist_demand_fan_delta` ou plus de la cible, relâché à la moitié de cet écart ; le mode du bloc programmé reprend alors. Ignoré si l'appareil ne propose pas ce mode. Diagnostic `demand_fan_mode`. |
| `room_sensor_assist_demand_fan_delta` | `1.5` (0.5 à 5) | Écart pièce/cible, en degrés, qui déclenche la ventilation de rattrapage. |

Compromis de la limite directionnelle : Room Assist ne peut plus baisser la consigne pour
freiner un dépassement.

## Suivre upstream

Le dernier commit de la branche (« Build frontend bundle ») ne contient que le bundle
compilé. Il entre en conflit à chaque version upstream : on le retire avant le rebase et
on le refait après.

```bash
git fetch upstream --tags
git push origin upstream/main:main
git reset --hard HEAD~1
git rebase vX.Y.Z
(cd frontend && npm ci && npm run test && npm run build:release)
python3 -m unittest discover -s tests
git commit -am "Build frontend bundle"
git push --force-with-lease origin snakl/room-assist
git tag vX.Y.Z-snakl.1 && git push origin vX.Y.Z-snakl.1
```

La version du manifeste reste celle d'upstream ; c'est le tag `vX.Y.Z-snakl.N` qui identifie
le fork dans HACS. Si le rebase est en conflit, il ne peut l'être que dans les lignes d'appel
de `scheduler.py`, `models.py`, `api.py` ou `sensors-view.ts`. Quand upstream livre une de
ces options, supprimer la nôtre plutôt que de garder les deux.
