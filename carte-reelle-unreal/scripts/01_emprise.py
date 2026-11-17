"""Étape 1 - Emprise et repère local de la zone.

Lit zone.json (bbox WGS84, polygone GeoJSON/KML, ou tracé GPX/GeoJSON/KML + largeur de couloir),
choisit la projection (Lambert-93 en France métropolitaine, UTM ailleurs), fixe l'origine du repère
local au centre de la zone de détail (emprise + marge), arrondie au mètre, et dimensionne le carré
du terrain (heightmap) à une taille valide pour un Landscape Unreal.

Usage : python 01_emprise.py --zone zone.json --sortie DOSSIER
Sorties : DOSSIER/repere.json, DOSSIER/emprise.geojson (WGS84), DOSSIER/journaux/01_emprise.json
"""
import json

from shapely.geometry import mapping, shape

import geo


def main():
    ap = geo.parser(__doc__.splitlines()[0])
    args = ap.parse_args()
    if not args.zone:
        ap.error("--zone est obligatoire pour cette étape")
    ctx = geo.Contexte(args)
    rep = ctx.repere
    t = rep["terrain"]
    feats = []
    for nom in ("emprise_locale", "zone_detail_locale", "trace_locale"):
        if nom in rep:
            g = geo.appliquer(shape(rep[nom]), lambda x, y: ctx.local_vers_lonlat(x, y))
            feats.append({"type": "Feature", "properties": {"role": nom.replace("_locale", "")}, "geometry": mapping(g)})
    geo.ecrire_geojson(ctx.sortie / "emprise.geojson", feats)
    b = rep["bornes_detail_locales"]
    ctx.journal("01_emprise", {"crs": rep["crs"], "france": rep["france"], "origine_proj": rep["origine_proj"],
                               "origine_wgs84": rep["origine_wgs84"], "terrain": t,
                               "surface_emprise_ha": rep["surface_emprise_ha"], "bornes_detail_locales": b})
    lignes = [f"01_emprise : {rep['nom']} ({rep['type_emprise']}), {rep['crs']}, origine "
              f"{rep['origine_wgs84'][0]:.5f}, {rep['origine_wgs84'][1]:.5f} ; emprise {rep['surface_emprise_ha']} ha, "
              f"détail {b[2] - b[0]:.0f} x {b[3] - b[1]:.0f} m",
              f"  terrain : heightmap {t['taille_px']} px au pas {t['pas_m']} m = {t['cote_m']:.0f} m de côté"]
    if t["note"]:
        lignes.append("  ATTENTION : " + t["note"])
    if not rep["france"]:
        lignes.append("  hors France : fournir --mnt et --ortho aux étapes 02 et 03 ; vecteurs par OSM seulement")
    geo.resume(lignes)


if __name__ == "__main__":
    main()
