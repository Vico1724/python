"""Étape 4 - Vecteurs : BD TOPO (WFS Géoplateforme) et OpenStreetMap (Overpass) en repère local.

BD TOPO : routes (nature, largeur de chaussée, nombre de voies), bâtiments (hauteur, altitudes),
végétation, haies, hydrographie, constructions linéaires/ponctuelles/surfaciques, lignes
électriques, terrains de sport. OSM complète (arbres isolés, murs, clôtures, chemins récents) et
remplace la BD TOPO hors de France. Overpass est souvent saturé : plusieurs miroirs sont essayés,
et son absence n'arrête pas l'étape en France.
Chaque couche est découpée à la zone de détail (emprise + marge) et écrite en coordonnées locales
(x est, y nord, mètres, arrondies au cm), sans les attributs vides.

Usage : python 04_vecteurs.py --zone zone.json --sortie DOSSIER [--sans-osm]
Sorties : vecteurs/bdtopo_<couche>.geojson, vecteurs/osm_<categorie>.geojson, journaux/04_vecteurs.json
"""
import json

import shapely
from shapely.geometry import LineString, Point, Polygon, mapping, shape
from shapely.ops import polygonize, unary_union

import geo

COUCHES_BDTOPO = {
    "routes": "BDTOPO_V3:troncon_de_route",
    "batiments": "BDTOPO_V3:batiment",
    "vegetation": "BDTOPO_V3:zone_de_vegetation",
    "haies": "BDTOPO_V3:haie",
    "construction_lineaire": "BDTOPO_V3:construction_lineaire",
    "construction_ponctuelle": "BDTOPO_V3:construction_ponctuelle",
    "construction_surfacique": "BDTOPO_V3:construction_surfacique",
    "hydro_lignes": "BDTOPO_V3:troncon_hydrographique",
    "hydro_surfaces": "BDTOPO_V3:surface_hydrographique",
    "lignes_electriques": "BDTOPO_V3:ligne_electrique",
    "pylones": "BDTOPO_V3:pylone",
    "terrains_de_sport": "BDTOPO_V3:terrain_de_sport",
    "voies_ferrees": "BDTOPO_V3:troncon_de_voie_ferree",
}
# Attributs BD TOPO inutiles pour un décor (identifiants de sources, dates de saisie...) : retirés pour alléger.
ATTR_IGNORES = ("date_creation", "date_modification", "date_d_apparition", "date_de_confirmation", "sources",
                "identifiants_sources", "methode_d_acquisition_planimetrique", "methode_d_acquisition_altimetrique",
                "precision_planimetrique", "precision_altimetrique", "gcms_detruit", "gcms_date_creation",
                "gcms_date_modification", "gcms_territoire", "gcms_fingerprint")

# Catégories OSM : (filtre Overpass, géométrie attendue)
OSM = {
    "routes": ('way["highway"]', "ligne"),
    "batiments": ('way["building"];relation["building"]', "surface"),
    "vegetation": ('way["natural"~"^(wood|scrub|heath|grassland)$"];way["landuse"~"^(forest|orchard|vineyard|grass|meadow)$"];'
                   'relation["natural"="wood"];relation["landuse"="forest"]', "surface"),
    "arbres": ('node["natural"="tree"];way["natural"="tree_row"]', "point_ou_ligne"),
    "hydro": ('way["waterway"];way["natural"="water"];relation["natural"="water"]', "mixte"),
    "lineaires": ('way["barrier"~"^(wall|fence|retaining_wall|hedge|guard_rail)$"]', "ligne"),
}


def nettoyer(props):
    return {k: v for k, v in props.items() if v not in (None, "") and k not in ATTR_IGNORES}


def decouper(ctx, geom_proj, zone):
    g = shapely.force_2d(geom_proj)
    g = geo.appliquer(g, lambda x, y: (x - ctx.ox, y - ctx.oy))
    if not g.is_valid:
        g = g.buffer(0) if g.geom_type in ("Polygon", "MultiPolygon") else g
    g = g.intersection(zone)
    return None if g.is_empty else shapely.set_precision(g, 0.01)


def bdtopo(ctx, zone, bbox, dossier):
    comptes, echecs = {}, {}
    for nom, typename in COUCHES_BDTOPO.items():
        try:
            feats = geo.wfs_couche(ctx.cache, typename, bbox, srs=ctx.crs)
        except Exception as e:          # une couche absente ne bloque pas les autres
            echecs[nom] = str(e)[:200]
            continue
        out = []
        for f in feats:
            if not f.get("geometry"):
                continue
            g = decouper(ctx, shape(f["geometry"]), zone)
            if g is not None:
                out.append({"type": "Feature", "id": f.get("id"), "properties": nettoyer(f["properties"]),
                            "geometry": mapping(g)})
        geo.ecrire_geojson(dossier / f"bdtopo_{nom}.geojson", out, source="BD TOPO IGN, Licence Ouverte Etalab 2.0",
                           repere="local (x est, y nord, m)")
        comptes[nom] = len(out)
    return comptes, echecs


def requete_osm(bbox_lonlat):
    s, o, n, e = bbox_lonlat[1], bbox_lonlat[0], bbox_lonlat[3], bbox_lonlat[2]
    bb = f"({s:.6f},{o:.6f},{n:.6f},{e:.6f})"
    parts = "".join(f"{q}{bb};" for filtre, _ in OSM.values() for q in filtre.split(";"))
    return f"[out:json][timeout:50];({parts});out geom tags;"


def geom_osm(el):
    t = el.get("tags", {})
    if el["type"] == "node":
        return Point(el["lon"], el["lat"])
    if el["type"] == "way":
        pts = [(p["lon"], p["lat"]) for p in el.get("geometry", []) if p]
        if len(pts) < 2:
            return None
        ferme = pts[0] == pts[-1] and len(pts) >= 4
        surface = ferme and ("building" in t or t.get("natural") in ("wood", "scrub", "heath", "grassland", "water")
                             or "landuse" in t or t.get("area") == "yes")
        return Polygon(pts) if surface else LineString(pts)
    if el["type"] == "relation":            # multipolygone : on recompose les anneaux extérieurs
        lignes = [LineString([(p["lon"], p["lat"]) for p in m["geometry"]]) for m in el.get("members", [])
                  if m.get("role") == "outer" and len(m.get("geometry", [])) >= 2]
        polys = list(polygonize(unary_union(lignes))) if lignes else []
        return unary_union(polys) if polys else None
    return None


def categorie(t):
    if "building" in t:
        return "batiments"
    if "highway" in t:
        return "routes"
    if t.get("natural") in ("tree", "tree_row"):
        return "arbres"
    if "waterway" in t or t.get("natural") == "water":
        return "hydro"
    if "barrier" in t:
        return "lineaires"
    if t.get("natural") or t.get("landuse"):
        return "vegetation"
    return None


def osm(ctx, zone, bbox, dossier):
    budget = float(ctx.cfg["osm_budget_s"]) if ctx.en_france() else max(float(ctx.cfg["osm_budget_s"]), 600.0)
    d, serveur = geo.overpass(ctx.cache, requete_osm(bbox), budget=budget)
    if d is None:
        return None, serveur
    par_cat = {c: [] for c in OSM}
    for el in d.get("elements", []):
        cat = categorie(el.get("tags", {}))
        if not cat:
            continue
        try:
            g = geom_osm(el)
        except Exception:               # géométrie OSM dégénérée : ignorée
            g = None
        if g is None or g.is_empty:
            continue
        g = decouper(ctx, geo.appliquer(g, ctx._vers_proj.transform), zone)
        if g is not None:
            par_cat[cat].append({"type": "Feature", "id": f"{el['type']}/{el['id']}", "properties": el.get("tags", {}),
                                 "geometry": mapping(g)})
    for cat, feats in par_cat.items():
        geo.ecrire_geojson(dossier / f"osm_{cat}.geojson", feats, source="OpenStreetMap, ODbL",
                           repere="local (x est, y nord, m)")
    return {c: len(f) for c, f in par_cat.items()}, serveur


def main():
    ap = geo.parser(__doc__.splitlines()[0])
    ap.add_argument("--sans-osm", action="store_true", help="n'interroge pas Overpass")
    args = ap.parse_args()
    ctx = geo.Contexte(args)
    d = ctx.dossier("vecteurs")
    avec_osm = ctx.cfg["osm"] and not args.sans_osm
    j = ctx.deja_fait("04_vecteurs", [d], osm=avec_osm)
    if j and (not avec_osm or j.get("osm")):
        geo.resume([f"04_vecteurs : déjà fait ({j['resume']}) ; --force pour refaire"])
        return
    pj = ctx.sortie / "journaux" / "04_vecteurs.json"
    if pj.exists() and json.loads(pj.read_text(encoding="utf-8")).get("signature") != ctx.signature:
        for g in d.glob("*.geojson"):         # zone.json a changé : pas de couche d'une ancienne emprise
            g.unlink()
    zone = ctx.emprise_locale()
    bbox = ctx.bbox_lonlat(*zone.bounds)
    comptes, echecs = ({}, {})
    if ctx.en_france():
        comptes, echecs = bdtopo(ctx, zone, bbox, d)
    c_osm, serveur = (None, "désactivé")
    if avec_osm:
        c_osm, serveur = osm(ctx, zone, bbox, d)
    if not ctx.en_france() and c_osm is None:
        raise SystemExit("ERREUR 04_vecteurs : zone hors France (pas de BD TOPO) et OpenStreetMap injoignable "
                         f"({serveur}). Réessayer plus tard, ou déposer des GeoJSON en repère local dans "
                         f"{d} (osm_routes.geojson, osm_batiments.geojson, osm_vegetation.geojson).")
    txt = ("BD TOPO " + ", ".join(f"{k} {v}" for k, v in comptes.items() if k in ("routes", "batiments", "vegetation"))
           if comptes else "BD TOPO non (hors France)")
    txt += " ; OSM " + (", ".join(f"{k} {v}" for k, v in c_osm.items()) if c_osm else
                         "indisponible" if avec_osm else "désactivé")
    ctx.journal("04_vecteurs", {"options": {"osm": avec_osm}, "resume": txt, "bdtopo": comptes,
                                "bdtopo_echecs": echecs, "osm": c_osm, "osm_serveur": serveur})
    lignes = [f"04_vecteurs : {txt}"]
    if echecs:
        lignes.append(f"  couches BD TOPO en échec : {', '.join(echecs)} (détail dans journaux/04_vecteurs.json)")
    if c_osm is None and avec_osm:
        lignes.append("  OSM injoignable (miroirs essayés) : étape poursuivie avec la BD TOPO seule")
    lignes.append(f"  téléchargé : {geo.volume_telecharge()} ; {ctx.duree()}")
    geo.resume(lignes)


if __name__ == "__main__":
    main()
