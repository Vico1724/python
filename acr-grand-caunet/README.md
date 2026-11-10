# ES « Le Grand Caunet » pour Assetto Corsa Rally

Reproduction de l'épreuve spéciale « Le Grand Caunet » (6,702 km, asphalte, Sainte-Baume Rallye 2026, Bouches-du-Rhône) pour la simulation.

![Carte générale](figures/carte_generale.png)

## État du projet

| Phase | Contenu | État |
|---|---|---|
| 0 | Étude de faisabilité | Fait : [`docs/01_etude_faisabilite.md`](docs/01_etude_faisabilite.md) |
| 1 | Choix de la spéciale | Fait : ES « Le Grand Caunet », 6,702 km |
| 2 | Identification GPS, cartographie, relief, données géographiques | Fait : [`docs/02_phase2_donnees_geographiques.md`](docs/02_phase2_donnees_geographiques.md) |
| 3 | Axe et bords de chaussée précis, dévers, lignes de départ et d'arrivée | À faire |
| 4 à 8 | Terrain 3D, route, décor, export vers le jeu, notes du copilote, tests | À faire |

**À savoir avant tout** : Assetto Corsa Rally (version 0.6) ne propose officiellement que des livrées personnalisées. Des spéciales non officielles existent pourtant depuis fin octobre 2026, dont une construite à partir de données cartographiques publiques. Le projet vise donc Assetto Corsa Rally par cette voie non officielle, encore expérimentale, en gardant des données et un modèle 3D indépendants du jeu. Le détail est dans l'étude de faisabilité.

## Contenu

```
docs/                 étude de faisabilité, rapport de phase 2, vidéos embarquées,
                      guide de ce que le directeur fait sur son PC
figures/              carte générale, profil en long, zooms départ et arrivée
data/reference/       points GPS et PK de la carte officielle de l'organisateur
data/processed/       tracé (GeoJSON, GPX, KML), profil au mètre, virages, ponts,
                      carrefours, relief à 1 m, décor dans le couloir
data/raw/             relief 0,5 m, photo aérienne 20 cm (non versionnés, 220 Mo)
scripts/              chaîne de traitement, rejouable de bout en bout
```

Pour voir le tracé sans rien installer : ouvrir `data/processed/trace_es.kml` dans Google Earth.

## Rejouer la phase 2

```bash
pip install -r requirements.txt
scripts/tout_lancer.sh        # quelques minutes, accès à data.geopf.fr requis
```

## Sources et licences

- Données géographiques : IGN (LiDAR HD, BD ORTHO, BD TOPO, BD Forêt), Licence Ouverte Etalab 2.0.
- Points de l'ES : carte officielle de l'ASA Marseille Provence Métropole, dont seules les coordonnées et distances sont reprises.
