"""Étape 1 - Télécharge les couches vectorielles IGN de l'emprise (BD TOPO, BD Forêt).

Sortie : data/raw/<couche>.geojson (bruts, non versionnés, WGS84 avec altitude
quand la BD TOPO la fournit).
"""
import json

from acr_geo import RAW, wfs_layer

LAYERS = {
    # nom local            : couche WFS de la Géoplateforme
    "troncon_de_route":       "BDTOPO_V3:troncon_de_route",
    "batiment":               "BDTOPO_V3:batiment",
    "zone_de_vegetation":     "BDTOPO_V3:zone_de_vegetation",
    "haie":                   "BDTOPO_V3:haie",
    "construction_lineaire":  "BDTOPO_V3:construction_lineaire",
    "construction_ponctuelle": "BDTOPO_V3:construction_ponctuelle",
    "construction_surfacique": "BDTOPO_V3:construction_surfacique",
    "ligne_electrique":       "BDTOPO_V3:ligne_electrique",
    "pylone":                 "BDTOPO_V3:pylone",
    "troncon_hydrographique": "BDTOPO_V3:troncon_hydrographique",
    "surface_hydrographique": "BDTOPO_V3:surface_hydrographique",
    "reservoir":              "BDTOPO_V3:reservoir",
    "detail_orographique":    "BDTOPO_V3:detail_orographique",
    "ligne_orographique":     "BDTOPO_V3:ligne_orographique",
    "lieu_dit_non_habite":    "BDTOPO_V3:lieu_dit_non_habite",
    "zone_d_activite":        "BDTOPO_V3:zone_d_activite_ou_d_interet",
    "equipement_de_transport": "BDTOPO_V3:equipement_de_transport",
    "terrain_de_sport":       "BDTOPO_V3:terrain_de_sport",
    "commune":                "BDTOPO_V3:commune",
    "bdforet_formation_vegetale": "LANDCOVER.FORESTINVENTORY.V2:formation_vegetale",
}

if __name__ == "__main__":
    for name, typename in LAYERS.items():
        try:
            feats = wfs_layer(typename)
        except Exception as e:  # une couche absente ne bloque pas les autres
            print(f"{name:28s} ECHEC {e}")
            continue
        (RAW / f"{name}.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
            encoding="utf-8")
        print(f"{name:28s} {len(feats):6d} entités")
