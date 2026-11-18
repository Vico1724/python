"""Étape 8 - Paquet neutre pour Unreal Engine 5 (et pour tout adaptateur de jeu).

Rassemble dans DOSSIER/paquet_unreal/ :
  terrain/heightmap_<N>.png (+ .r16), terrain/ortho_terrain.jpg   Landscape et sa texture (02, 03)
  maillages/terrain_proche.glb, lointain.glb                       relief texturé (07)
  maillages/batiments.glb                                          volumes extrudés (emprise BD TOPO ou OSM)
  maillages/routes.glb                                             rubans de chaussée posés sur le relief
  placements/arbres.csv                                            x,y,z,hauteur,rayon,type (05)
  placements/batiments.json, routes.json                           données brutes pour un adaptateur
  vecteurs/*.geojson, photos/photos_rue.csv                        couches en repère local, références
  table_assets.csv                                                 type -> asset Unreal (à remplir)
  manifeste.json, LISEZMOI_import.md, importer_paquet.py           description, consignes, script d'éditeur
Bâtiments : base = sol le plus bas sous l'emprise ; hauteur BD TOPO, sinon LiDAR (MNS - sol, 75e
centile), sinon étages x 3 m, sinon 6 m. Routes : largeur de chaussée BD TOPO, sinon voies x 3,25 m,
sinon une largeur type selon la nature ; ponts et tunnels (position hors sol) gardés dans
routes.json mais sans ruban.

Usage : python 08_paquet_unreal.py --zone zone.json --sortie DOSSIER [--table table_assets.csv]
Sorties : DOSSIER/paquet_unreal/ (voir ci-dessus), journaux/08_paquet_unreal.json
"""
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import shapely
import trimesh
from shapely.geometry import shape

import geo

ICI = Path(__file__).resolve().parent
TABLE_EXEMPLE = ICI.parent / "assets" / "table_assets_exemple.csv"
H_ETAGE = 3.0            # m par étage quand seule la hauteur en étages est connue
H_DEFAUT = 6.0           # m : bâtiment sans aucune information de hauteur (deux niveaux)
SURF_MIN = 4.0           # m² : en dessous, abri ou erreur de saisie, ignoré
PAS_ROUTE = 5.0          # m entre deux points d'une route posée sur le relief
DESSUS_ROUTE = 0.10      # m : ruban au-dessus du Landscape pour ne pas scintiller
ENTERRE = 0.5            # m : les bâtiments descendent sous le sol le plus bas (pas de jour sous les murs)
# Largeur type (m) quand la BD TOPO ne donne ni largeur ni nombre de voies (et pour OSM).
LARGEURS = {"Autoroute": 10.5, "Quasi-autoroute": 10.5, "Route à 2 chaussées": 7.0, "Route à 1 chaussée": 5.5,
            "Bretelle": 5.0, "Rond-point": 7.0, "Route empierrée": 3.5, "Chemin": 3.0, "Sentier": 1.2,
            "Escalier": 2.0, "Piste cyclable": 2.5, "Bac ou liaison maritime": 0.0,
            "motorway": 10.5, "trunk": 7.5, "primary": 7.0, "secondary": 6.5, "tertiary": 6.0,
            "unclassified": 5.0, "residential": 5.5, "service": 3.5, "living_street": 4.5, "track": 3.0,
            "path": 1.2, "footway": 1.5, "cycleway": 2.5, "steps": 2.0, "pedestrian": 4.0}


def lire_mns(ctx):
    p = ctx.sortie / "relief" / "mns_50cm.tif"
    if not p.exists():
        return None
    from affine import Affine
    a, tr = geo.lire_tif(p)
    return a, Affine(tr.a, 0, tr.c - ctx.ox, 0, tr.e, tr.f - ctx.oy)


def nombre(v):
    try:
        return float(str(v).split()[0].replace(",", "."))
    except (TypeError, ValueError, IndexError):
        return None


def batiments(ctx, rel, mns):
    feats = geo.lire_geojson(ctx.sortie / "vecteurs" / "bdtopo_batiments.geojson")
    source = "BD TOPO"
    if not feats:
        feats, source = geo.lire_geojson(ctx.sortie / "vecteurs" / "osm_batiments.geojson"), "OSM"
    out, maillages, sources_h = [], [], {}
    for k, f in enumerate(feats):
        p = f["properties"]
        for poly in geo.polygones(shape(f["geometry"])):
            poly = poly.buffer(0).simplify(0.2)
            if poly.is_empty or poly.geom_type != "Polygon" or poly.area < SURF_MIN:
                continue
            ext = np.asarray(poly.exterior.coords)
            zs = rel.z(np.append(ext[:, 0], poly.centroid.x), np.append(ext[:, 1], poly.centroid.y))
            z_sol = float(zs.min())
            h, src = nombre(p.get("hauteur")), "bdtopo"
            if not h or h <= 0:
                h, src = None, None
                if mns is not None:
                    x0, y0, x1, y1 = poly.bounds
                    gx, gy = np.meshgrid(np.arange(x0, x1, 1.0), np.arange(y0, y1, 1.0))
                    m = shapely.contains_xy(poly, gx.ravel(), gy.ravel())
                    if m.sum() >= 3:
                        v = geo.echantillonner(mns[0], mns[1], gx.ravel()[m], gy.ravel()[m]) - ctx.repere["z0_m"]
                        hh = float(np.percentile(v, 75)) - z_sol
                        if 2.0 <= hh <= 150:
                            h, src = hh, "lidar"
                if h is None:
                    et = nombre(p.get("nombre_d_etages") or p.get("building:levels"))
                    oh = nombre(p.get("height"))
                    h, src = (oh, "osm_height") if oh else ((et * H_ETAGE, "etages") if et else (H_DEFAUT, "defaut"))
            sources_h[src] = sources_h.get(src, 0) + 1
            try:
                m = trimesh.creation.extrude_polygon(poly, h + ENTERRE)
            except Exception:           # polygone que la triangulation refuse : ignoré
                continue
            v = m.vertices
            m.vertices = geo.gltf(v[:, 0], v[:, 1], v[:, 2] + z_sol - ENTERRE)
            maillages.append(m)
            out.append({"id": f.get("id") or f"bat_{k}", "source": source, "nature": p.get("nature") or p.get("building"),
                        "usage": p.get("usage_1"), "z_sol_m": round(z_sol, 2), "hauteur_m": round(h, 1),
                        "source_hauteur": src, "surface_m2": round(poly.area, 1),
                        "centre": [round(poly.centroid.x, 2), round(poly.centroid.y, 2)],
                        "emprise": [[round(x, 2), round(y, 2)] for x, y in ext],
                        "trous": [[[round(x, 2), round(y, 2)] for x, y in r.coords] for r in poly.interiors]})
    if not maillages:
        return out, None, sources_h
    mesh = trimesh.util.concatenate(maillages)
    mesh.visual = trimesh.visual.ColorVisuals(mesh, vertex_colors=np.tile([190, 186, 178, 255], (len(mesh.vertices), 1)))
    return out, mesh, sources_h


def largeur_route(p):
    l = nombre(p.get("largeur_de_chaussee")) or nombre(p.get("width"))
    if l and l > 0:
        return l, "mesuree"
    v = nombre(p.get("nombre_de_voies")) or nombre(p.get("lanes"))
    if v and v > 0:
        return v * 3.25, "voies"
    return LARGEURS.get(p.get("nature") or p.get("highway"), 4.0), "type"


def routes(ctx, rel):
    feats = geo.lire_geojson(ctx.sortie / "vecteurs" / "bdtopo_routes.geojson")
    source = "BD TOPO"
    if not feats:
        feats, source = geo.lire_geojson(ctx.sortie / "vecteurs" / "osm_routes.geojson"), "OSM"
    out, V, F = [], [], []
    for k, f in enumerate(feats):
        p = f["properties"]
        larg, src_l = largeur_route(p)
        pos = str(p.get("position_par_rapport_au_sol", "0"))
        if p.get("bridge") or p.get("tunnel"):
            pos = "1" if p.get("bridge") else "-1"
        for ligne in geo.lignes(shape(f["geometry"])):
            if ligne.length < 0.5:
                continue
            d = np.append(np.arange(0, ligne.length, PAS_ROUTE), ligne.length)
            pts = np.array([ligne.interpolate(s).coords[0] for s in d])
            z = rel.z(pts[:, 0], pts[:, 1])
            out.append({"id": f.get("id") or f"route_{k}", "source": source, "nature": p.get("nature") or p.get("highway"),
                        "importance": p.get("importance"), "nom": p.get("nom_collaboratif_gauche") or p.get("name"),
                        "largeur_m": round(larg, 2), "source_largeur": src_l, "voies": p.get("nombre_de_voies") or p.get("lanes"),
                        "position_sol": pos, "sens": p.get("sens_de_circulation") or p.get("oneway"),
                        "revetement": p.get("surface"),
                        "points": [[round(a, 2), round(b, 2), round(c, 2)] for a, b, c in zip(pts[:, 0], pts[:, 1], z)]})
            if pos != "0" or larg <= 0:
                continue
            t = np.gradient(pts, axis=0)
            t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
            nrm = np.column_stack([-t[:, 1], t[:, 0]]) * larg / 2
            g, dr = pts + nrm, pts - nrm
            zg, zd = rel.z(g[:, 0], g[:, 1]), rel.z(dr[:, 0], dr[:, 1])
            base = sum(len(v) for v in V)
            V.append(geo.gltf(np.concatenate([g[:, 0], dr[:, 0]]), np.concatenate([g[:, 1], dr[:, 1]]),
                              np.concatenate([np.maximum(zg, z), np.maximum(zd, z)]) + DESSUS_ROUTE))
            n = len(pts)
            i = np.arange(n - 1)
            F.append(np.concatenate([np.column_stack([i, i + n, i + 1]), np.column_stack([i + 1, i + n, i + 1 + n])]) + base)
    if not V:
        return out, None
    mesh = trimesh.Trimesh(np.concatenate(V), np.concatenate(F), process=False)
    mesh.visual = trimesh.visual.ColorVisuals(mesh, vertex_colors=np.tile([70, 70, 72, 255], (len(mesh.vertices), 1)))
    return out, mesh


def copier(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    return dst


def lisezmoi(man):
    L = man["landscape"]
    e = L["echelle_cm"]
    lignes = [
        f"# Paquet Unreal : {man['nom']}", "",
        f"Créé le {man['cree_le'][:10]} par la chaîne carte-reelle-unreal. Repère : {man['repere']['crs']}, "
        f"origine {man['repere']['origine_wgs84'][0]:.6f}, {man['repere']['origine_wgs84'][1]:.6f} "
        f"(WGS84), z0 = {man['repere']['z0_m']} m d'altitude.", "",
        "## Axes et unités",
        "- Données (CSV, JSON, GeoJSON) : x = est, y = nord, z = altitude - z0, en mètres.",
        "- Unreal : X = 100 x, Y = -100 y (Y Unreal vers le sud), Z = 100 z, en centimètres.",
        "- Fichiers .glb : X = est, Y = haut, Z = sud (mètres) ; l'importeur glTF d'Unreal les place directement "
        "(UE = 100 (gX, gZ, gY)). Le script vérifie les bornes importées contre manifeste.json.", "",
        "## Import automatique (éditeur Unreal 5.x)",
        "Outils > Exécuter un script Python, ou dans la console : `py \"<chemin>/importer_paquet.py\" --paquet \"<chemin du paquet>\"`.",
        "Remplir d'abord `table_assets.csv` (type d'arbre -> asset du projet) ; par défaut, des formes de base grises.",
        "Le script n'a pas été exécuté dans l'environnement qui l'a écrit : lire son rapport (Saved/CarteReelle/).", "",
        "## Landscape (à faire à la main si le script ne peut pas le créer)",
        f"1. Mode Landscape > Manage > New > Import from File : `{L['fichier']}` ({L['taille_px']} x {L['taille_px']} px).",
        f"2. Location : X {L['position_centre_cm'][0]}, Y {L['position_centre_cm'][1]}, Z {L['position_centre_cm'][2]} "
        "(l'outil centre le Landscape sur ce point).",
        f"3. Scale : X {e['x']}, Y {e['y']}, Z {e['z']}. Laisser la résolution proposée (elle doit valoir {L['taille_px']}).",
        f"4. Matériau : texture `{L['texture']}` en UV 0-1 sur tout le Landscape "
        "(Landscape Coordinates, Mapping Scale = taille en quads, ou un matériau à UV mondiales).",
        f"Contrôle : le sol au centre doit être à Z ≈ 0 ; altitudes du terrain de {L['z_min_m']} à {L['z_max_m']} m (relatives à z0).", "",
        "## Contenu", "",
        "| fichier | rôle |", "|---|---|"]
    lignes += [f"| `{f['chemin']}` | {f['role']} |" for f in man["fichiers"]]
    lignes += ["", "## Sources et licences"] + [f"- {s}" for s in man["sources"]]
    return "\n".join(lignes) + "\n"


def main():
    ap = geo.parser(__doc__.splitlines()[0])
    ap.add_argument("--table", help="table type -> asset remplie (CSV) à mettre dans le paquet")
    args = ap.parse_args()
    ctx = geo.Contexte(args)
    rep = ctx.repere
    manque = [k for k in ("unreal_landscape", "ortho", "maillages") if not rep.get(k)]
    if manque:
        raise SystemExit(f"ERREUR 08_paquet_unreal : étapes précédentes manquantes ({', '.join(manque)}) : lancer 02, 03 et 07")
    P = ctx.sortie / "paquet_unreal"
    P.mkdir(exist_ok=True)
    S = ctx.sortie
    rel = geo.Relief(ctx)
    fichiers = []

    def ajoute(chemin, role, **extra):
        fichiers.append({"chemin": str(chemin.relative_to(P)).replace("\\", "/"), "role": role,
                         "octets": chemin.stat().st_size, **extra})

    L = rep["unreal_landscape"]
    hm = copier(S / "relief" / L["fichier"], P / "terrain" / L["fichier"])
    ajoute(hm, "heightmap 16 bits du Landscape (PNG niveaux de gris)", format="png16")
    r16 = S / "relief" / L["fichier"].replace(".png", ".r16")
    if r16.exists():
        ajoute(copier(r16, P / "terrain" / r16.name), "même heightmap en RAW 16 bits petit-boutiste", format="r16")
    tex = copier(S / rep["ortho"]["terrain"]["fichier"], P / "terrain" / "ortho_terrain.jpg")
    ajoute(tex, "orthophoto du Landscape, UV 0-1 sur toute son étendue", format="jpg")
    tex_l = copier(S / rep["ortho"]["lointain"]["fichier"], P / "maillages" / "ortho_lointain.jpg")
    ajoute(tex_l, "orthophoto du lointain (déjà incluse dans lointain.glb)", format="jpg")

    maillages = []
    for nom, info in rep["maillages"].items():
        dst = copier(S / info["fichier"], P / "maillages" / Path(info["fichier"]).name)
        ajoute(dst, {"lointain": "relief lointain texturé, sans collision",
                     "terrain_proche": "relief du terrain en maillage texturé (aperçu ou secours du Landscape)"}[nom], format="glb")
        maillages.append({"nom": "SM_" + "".join(w.capitalize() for w in nom.split("_")), "fichier": dst.relative_to(P).as_posix(),
                          "role": nom, "bornes_cm": info["bornes_cm"],
                          "collision": "aucune" if nom == "lointain" else "complexe",
                          "poser": nom == "lointain", "ombre": nom != "lointain"})

    bats, m_bat, src_h = batiments(ctx, rel, lire_mns(ctx))
    (P / "placements").mkdir(exist_ok=True)
    pj = P / "placements" / "batiments.json"
    pj.write_text(json.dumps({"repere": "local (m)", "batiments": bats}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ajoute(pj, "bâtiments : emprise, sol, hauteur et sa source", format="json", nombre=len(bats))
    if m_bat is not None:
        b = geo.ecrire_glb(P / "maillages" / "batiments.glb", [("SM_Batiments", m_bat)])
        ajoute(P / "maillages" / "batiments.glb", "volumes simples des bâtiments (extrusion de l'emprise)", format="glb")
        maillages.append({"nom": "SM_Batiments", "fichier": "maillages/batiments.glb", "role": "batiments", "bornes_cm": b,
                          "collision": "complexe", "poser": True, "ombre": True, "couleur": [0.62, 0.60, 0.56]})
    rts, m_rt = routes(ctx, rel)
    pr = P / "placements" / "routes.json"
    pr.write_text(json.dumps({"repere": "local (m)", "routes": rts}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    ajoute(pr, "routes : polylignes 3D (pas de 5 m) avec largeur, nature, position", format="json", nombre=len(rts))
    if m_rt is not None:
        b = geo.ecrire_glb(P / "maillages" / "routes.glb", [("SM_Routes", m_rt)])
        ajoute(P / "maillages" / "routes.glb", "rubans de chaussée à 10 cm au-dessus du relief", format="glb")
        maillages.append({"nom": "SM_Routes", "fichier": "maillages/routes.glb", "role": "routes", "bornes_cm": b,
                          "collision": "aucune", "poser": True, "ombre": False, "couleur": [0.08, 0.08, 0.085]})

    n_arbres, types = 0, {}
    pa = S / "vegetation" / "arbres.csv"
    if pa.exists():
        dst = copier(pa, P / "placements" / "arbres.csv")
        with open(dst, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                n_arbres += 1
                types[r["type"]] = types.get(r["type"], 0) + 1
        ajoute(dst, "arbres : x,y,z (pied), hauteur, rayon du houppier, type", format="csv", nombre=n_arbres)
    for g in sorted((S / "vecteurs").glob("*.geojson")):
        ajoute(copier(g, P / "vecteurs" / g.name), "couche vectorielle en repère local", format="geojson",
               nombre=len(geo.lire_geojson(g)))
    pp = S / "photos" / "photos_rue.csv"
    if pp.exists():
        ajoute(copier(pp, P / "photos" / "photos_rue.csv"), "photos de rue Panoramax (référence, licence par image)", format="csv")
    tbl = P / "table_assets.csv"
    if args.table:
        copier(Path(args.table).resolve(), tbl)
    elif not tbl.exists():
        copier(TABLE_EXEMPLE, tbl)
    ajoute(tbl, "correspondance type -> asset Unreal, à remplir", format="csv")
    imp = ICI / "unreal" / "importer_paquet.py"
    if imp.exists():
        ajoute(copier(imp, P / "importer_paquet.py"), "script Python de l'éditeur Unreal (non exécuté hors Unreal)", format="py")
    shutil.copyfile(S / "repere.json", P / "repere.json")
    ajoute(P / "repere.json", "repère complet de la zone (copie)", format="json")

    sources = ["Relief : " + ("MNT fourni par l'utilisateur" if rep.get("mnt_fourni") else
                              "IGN LiDAR HD et RGE ALTI, Licence Ouverte Etalab 2.0"),
               "Orthophoto : " + rep["ortho"]["source"],
               "Vecteurs : BD TOPO IGN (Licence Ouverte Etalab 2.0) et OpenStreetMap (ODbL, attribution « © les contributeurs d'OpenStreetMap »)",
               "Photos de rue : Panoramax, licence indiquée image par image"]
    man = {"format": "carte-reelle-unreal/1", "nom": rep["nom"], "cree_le": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "repere": {k: rep[k] for k in ("crs", "origine_proj", "origine_wgs84", "z0_m", "axes", "type_emprise")},
           "unites": {"donnees": "m", "unreal": "cm", "angles": "degrés, cap 0 = nord, sens horaire"},
           "emprise_locale": rep["emprise_locale"], "bornes_detail_locales": rep["bornes_detail_locales"],
           "altitudes_m": {"min": rep["altitude_min_m"], "max": rep["altitude_max_m"]},
           "landscape": {**L, "fichier": f"terrain/{L['fichier']}", "texture": "terrain/ortho_terrain.jpg",
                         "pas_m": rep["terrain"]["pas_m"], "bornes_locales": rep["terrain"]["bornes_locales"]},
           "maillages": maillages,
           "placements": {"arbres": {"fichier": "placements/arbres.csv", "colonnes": ["x", "y", "z", "hauteur", "rayon", "type"],
                                     "nombre": n_arbres, "types": types, "table": "table_assets.csv"},
                          "batiments": {"fichier": "placements/batiments.json", "nombre": len(bats), "sources_hauteur": src_h},
                          "routes": {"fichier": "placements/routes.json", "nombre": len(rts)}},
           "fichiers": fichiers, "sources": sources}
    (P / "LISEZMOI_import.md").write_text(lisezmoi(man), encoding="utf-8")
    man["fichiers"].append({"chemin": "LISEZMOI_import.md", "role": "consignes d'import", "octets": (P / "LISEZMOI_import.md").stat().st_size})
    (P / "manifeste.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(p.stat().st_size for p in P.rglob("*") if p.is_file())
    txt = (f"{len(fichiers)} fichiers, {total / 1e6:.1f} Mo ; {n_arbres} arbres, {len(bats)} bâtiments, {len(rts)} routes")
    ctx.journal("08_paquet_unreal", {"options": {"table": args.table}, "resume": txt, "dossier": P,
                                     "sources_hauteur_batiments": src_h, "types_arbres": types})
    geo.resume([f"08_paquet_unreal : {txt}",
                "  hauteurs des bâtiments : " + ", ".join(f"{k} {v}" for k, v in src_h.items()),
                f"  paquet : {P} ; {ctx.duree()}"])


if __name__ == "__main__":
    main()
