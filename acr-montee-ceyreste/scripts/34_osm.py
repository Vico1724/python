"""Collecte OpenStreetMap systématique du couloir de la montée et de l'approche du village (demande du 18/11/2026 :
« le script OpenStreetMap est très important »).

Overpass (plusieurs miroirs, essais successifs, cache dans data/raw/osm/ : sans réseau, le cache sert ; sans cache ni
réseau, le script le dit et s'arrête proprement). Clés collectées : signalisation (traffic_sign, highway=give_way|stop|
street_lamp|bus_stop|milestone|traffic_signals, traffic_calming, crossing), voies (highway avec maxspeed, surface, lanes,
width, oneway, junction, tracktype, access, name), barrières (barrier=*), ouvrages et réseaux (man_made=*, power=*),
nature (natural=tree|tree_row|cliff|rock|scree|wood|scrub ; landuse), bâti (building avec building:levels, roof:shape,
roof:material), lieux (amenity, tourism, historic, place, name).
Sortie : data/processed/osm_couloir.geojson (Lambert-93 + repère local + PK et écart à l'axe pour ce qui est à moins de
60 m de la route modélisée ou dans l'approche du village), data/processed/osm_bilan.json (bilan par clé et valeur).
Licence : © contributeurs OpenStreetMap, ODbL 1.0.
"""
from __future__ import annotations

import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import requests
import shapely
from shapely.geometry import LineString, Point, mapping

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acr_geo import OUT, RAW, TO_L93, TO_WGS  # noqa: E402

MIROIRS = ["https://overpass.private.coffee/api/interpreter", "https://overpass-api.de/api/interpreter",
           "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
CACHE = RAW / "osm" / "couloir_complet.json"
BBOX = (43.204, 5.618, 43.240, 5.672)          # sud, ouest, nord, est : village + montée + Grand Caunet
REQ = """[out:json][timeout:120];
(
  nwr["traffic_sign"]({b}); nwr["highway"]({b}); nwr["barrier"]({b}); nwr["man_made"]({b}); nwr["power"]({b});
  nwr["natural"]({b}); nwr["landuse"]({b}); nwr["building"]({b}); nwr["amenity"]({b}); nwr["tourism"]({b});
  nwr["historic"]({b}); nwr["place"]({b}); nwr["traffic_calming"]({b}); nwr["crossing"]({b});
);
out geom tags;"""
CLES = ["traffic_sign", "highway", "barrier", "man_made", "power", "natural", "landuse", "building", "amenity", "tourism",
        "historic", "place", "traffic_calming", "crossing"]
DETAIL = ["maxspeed", "surface", "lanes", "width", "oneway", "junction", "tracktype", "access", "name", "building:levels",
          "roof:shape", "roof:material", "ref", "direction", "traffic_sign:direction", "height", "material"]


def telecharger():
    q = REQ.replace("{b}", ",".join(map(str, BBOX)))
    for u in MIROIRS:
        for essai in range(2):
            try:
                r = requests.post(u, data={"data": q}, timeout=180)
                if r.ok and r.text.lstrip().startswith("{"):
                    CACHE.parent.mkdir(parents=True, exist_ok=True)
                    CACHE.write_text(r.text, encoding="utf-8")
                    return u
            except requests.RequestException:
                pass
            time.sleep(3)
    return None


def api_osm():
    """Repli quand Overpass ne répond pas : API OSM v0.6 (/map) par dalles de 0,01 x 0,008 degré, converties au format
    d'Overpass (éléments avec tags et géométrie), filtrées aux clés suivies."""
    import xml.etree.ElementTree as ET
    noeuds, voies = {}, {}
    s_, w_, n_, e_ = BBOX
    for lo in np.arange(w_, e_, 0.01):
        for la in np.arange(s_, n_, 0.008):
            url = (f"https://api.openstreetmap.org/api/0.6/map?bbox={lo:.4f},{la:.4f},{min(lo + 0.01, e_):.4f},"
                   f"{min(la + 0.008, n_):.4f}")
            for essai in range(3):
                try:
                    r = requests.get(url, timeout=120, headers={"User-Agent": "acr-stage-geodata/1.0"})
                    if r.ok:
                        break
                except requests.RequestException:
                    pass
                time.sleep(5)
            else:
                print("dalle OSM manquante :", url)
                continue
            root = ET.fromstring(r.content)
            for nd in root.iter("node"):
                noeuds[nd.get("id")] = (float(nd.get("lat")), float(nd.get("lon")),
                                        {t.get("k"): t.get("v") for t in nd.iter("tag")})
            for w in root.iter("way"):
                voies[w.get("id")] = ([x.get("ref") for x in w.iter("nd")], {t.get("k"): t.get("v") for t in w.iter("tag")})
            time.sleep(1)
    el = []
    suivi = lambda t: any(k in t for k in CLES)                                  # noqa: E731
    for i, (la, lo, t) in noeuds.items():
        if suivi(t):
            el.append({"type": "node", "id": int(i), "lat": la, "lon": lo, "tags": t})
    for i, (refs, t) in voies.items():
        if suivi(t) and all(r in noeuds for r in refs):
            el.append({"type": "way", "id": int(i), "tags": t,
                       "geometry": [{"lat": noeuds[r][0], "lon": noeuds[r][1]} for r in refs]})
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({"elements": el, "source": "api.openstreetmap.org/api/0.6/map"}), encoding="utf-8")
    return "api.openstreetmap.org (API v0.6, repli)"


def geom(e):
    if e["type"] == "node":
        return Point(TO_L93.transform(e["lon"], e["lat"]))
    if "geometry" in e:
        c = [TO_L93.transform(p["lon"], p["lat"]) for p in e["geometry"] if p]
        if len(c) >= 2:
            return LineString(c)
    if "bounds" in e:
        b = e["bounds"]
        return Point(TO_L93.transform((b["minlon"] + b["maxlon"]) / 2, (b["minlat"] + b["maxlat"]) / 2))
    return None


def main():
    src = telecharger() or api_osm()
    if src is None and not CACHE.exists():
        print("Overpass injoignable et pas de cache : collecte OSM non faite (rien d'autre n'en dépend)")
        return
    print("source :", src or f"cache {CACHE.name}")
    d = json.loads(CACHE.read_text(encoding="utf-8"))
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as f:
        R = list(csv.DictReader(f))
    pk = np.array([float(r["pk_m"]) for r in R])
    axe = LineString([(float(r["x_axe"]), float(r["y_axe"])) for r in R])
    ref = json.loads((Path(__file__).resolve().parent.parent / "modele" / "repere.json").read_text(encoding="utf-8"))["origine"]
    appro = None
    fa = OUT / "village" / "approche.geojson"
    if fa.exists():
        g = shapely.geometry.shape(json.loads(fa.read_text(encoding="utf-8"))["features"][0]["geometry"])
        appro = shapely.transform(g, lambda c: np.column_stack(TO_L93.transform(c[:, 0], c[:, 1])))
    feats, bilan = [], Counter()
    proches = Counter()
    for e in d["elements"]:
        t = e.get("tags", {})
        g = geom(e)
        if g is None:
            continue
        dist = g.distance(axe)
        s = axe.project(g.centroid if g.geom_type != "Point" else g)
        pk_e = float(np.interp(s, np.r_[0, np.cumsum(np.hypot(*np.diff(np.array(axe.coords), axis=0).T))], pk))
        zone = "route" if dist < 60 else ("approche_village" if appro is not None and g.distance(appro) < 60 else "autour")
        for k in CLES:
            if k in t:
                bilan[f"{k}={t[k]}"] += 1
                if zone != "autour":
                    proches[f"{k}={t[k]} [{zone}]"] += 1
        c = g.centroid
        lon, lat = TO_WGS.transform(c.x, c.y)
        feats.append({"type": "Feature", "geometry": mapping(g),
                      "properties": {"osm": f"{e['type']}/{e['id']}", "zone": zone, "distance_axe_m": round(dist, 1),
                                     "pk_m": round(pk_e, 1) if zone == "route" else None,
                                     "x_local_m": round(c.x - ref["lambert93_x_m"], 2), "y_local_m": round(c.y - ref["lambert93_y_m"], 2),
                                     **{k: t[k] for k in CLES + DETAIL if k in t}}})
    gj = {"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:2154"}},
          "licence": "© contributeurs OpenStreetMap, ODbL 1.0", "features": [f for f in feats if f["properties"]["zone"] != "autour"]}
    (OUT / "osm_couloir.geojson").write_text(json.dumps(gj, ensure_ascii=False), encoding="utf-8")
    res = {"date": time.strftime("%Y-%m-%d"), "source": src or "cache", "elements_osm": len(d["elements"]),
           "dans_le_couloir_ou_l_approche": len(gj["features"]),
           "par_cle_dans_le_couloir": dict(sorted(proches.items(), key=lambda kv: -kv[1])),
           "par_cle_emprise_complete": dict(sorted(bilan.items(), key=lambda kv: -kv[1])[:150])}
    (OUT / "osm_bilan.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "par_cle_emprise_complete"}, ensure_ascii=False, indent=1)[:4000])


if __name__ == "__main__" and "croisement" not in sys.argv:
    main()
    croisement()


def croisement():
    """Recoupement en trois colonnes : objets ponctuels OSM du couloir (signalisation, barrières, arrêts, poteaux,
    arbres) face au relevé photo (releve_panoramax_2025.json) et à la BD TOPO / LiDAR (bâti, murs, pylônes : non
    ponctuels, pas de recoupement automatique). Écrit data/processed/osm_croisement.csv et renvoie le bilan."""
    from acr_geo import fichier_ref
    g = json.loads((OUT / "osm_couloir.geojson").read_text(encoding="utf-8"))
    rel = json.loads(fichier_ref("releve_panoramax_2025.json").read_text(encoding="utf-8"))["releve"]
    ponct = [e for e in rel if e["categorie"] == "ponctuel"]
    lignes, n = [], Counter()
    cles = ("traffic_sign", "barrier", "power", "natural")
    for f in g["features"]:
        p = f["properties"]
        if f["geometry"]["type"] != "Point" or p["zone"] != "route":
            continue
        quoi = next((f"{k}={p[k]}" for k in cles if k in p), None) or \
            (f"highway={p['highway']}" if p.get("highway") in ("give_way", "stop", "bus_stop", "milestone", "street_lamp") else None)
        if quoi is None or quoi in ("natural=scrub",):
            continue
        compat = {"traffic_sign": ("panneau",), "barrier": ("barriere", "portail"), "power": ("poteau",),
                  "highway": ("panneau", "abri", "borne"), "natural": ("arbre",)}[quoi.split("=")[0]]
        cand = [e for e in ponct if any(c in e["type"] for c in compat)]
        proche = min(cand, key=lambda e: abs(float(e["pk_m"]) - p["pk_m"]), default=None)
        vu = proche is not None and abs(float(proche["pk_m"]) - p["pk_m"]) < 20
        lignes.append({"osm": p["osm"], "objet": quoi, "pk_m": p["pk_m"], "distance_axe_m": p["distance_axe_m"],
                       "vu_osm": "oui", "vu_photo": f"oui ({proche['type']}, PK {proche['pk_m']})" if vu else "non relevé",
                       "bdtopo_lidar": "", "statut": "OSM + photo" if vu else "OSM seul"})
        n[lignes[-1]["statut"]] += 1
    osm_pk = [l["pk_m"] for l in lignes]
    for e in ponct:
        if not any(abs(float(e["pk_m"]) - float(l["pk_m"])) < 20 and l["vu_photo"].startswith(f"oui ({e['type']}")
                   for l in lignes):
            lignes.append({"osm": "", "objet": e["type"], "pk_m": e["pk_m"], "distance_axe_m": "", "vu_osm": "non",
                           "vu_photo": "oui", "bdtopo_lidar": "", "statut": "photo seule"})
            n["photo seule"] += 1
    with open(OUT / "osm_croisement.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(lignes[0])); w.writeheader(); w.writerows(sorted(lignes, key=lambda l: float(l["pk_m"])))
    print("recoupement :", dict(n))
    return dict(n)


if __name__ == "__main__" and "croisement" in sys.argv:
    croisement()
