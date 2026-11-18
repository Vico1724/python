"""Export neutre de la carte, indépendant d'Assetto Corsa Rally (demande du 18/11/2026 : « si on veut reuse cette carte
dans un autre jeu on a tout les model »).

Contenu de export/neutre/ :
  modeles/          toute la géométrie propre à la carte, en glb autonomes (textures intégrées ; terrain_sol.glb garde
                    ses images de dalles dans modeles/textures_sol/, à côté) : terrain proche, lointain, route et
                    marquage, ouvrages (murs, murets, parapets, glissières à nous, tabliers), carrefours, balisage,
                    bâti du bord de route, village, et les maillages fabriqués par le projet (pierres, blocs, poteau
                    de béton) repris du paquet Unreal ; NON VERSIONNÉ (lourd)
  collisions/       collisions séparées : sol physique et obstacles de l'export Stage IR, volumes des ouvrages, des
                    carrefours et des façades ; NON VERSIONNÉ
  placements/       un CSV par famille, sans rien du jeu : type, description, x, y, z (Lambert-93 / NGF et repère local),
                    cap, échelle, hauteur, source ; NON VERSIONNÉ (plusieurs Mo)
  correspondance_types.csv   type -> maillage ACR -> substitut libre (réel, forme simple, ou rien) ; versionné
  manifeste.json    repère, fichiers, tailles, bornes, comptes ; versionné
  controle.json     contrôle de l'export (fichiers, emprises, comptes, objets flottants ou enterrés) ; versionné
Aucun asset du jeu n'est extrait ni copié : les objets du jeu ne sont présents que par leur type et leur placement.
Usage : python scripts/33_export_neutre.py   (après 16_paquet_unreal.py)
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import struct
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import map_coordinates

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acr_geo import RAW, ROOT  # noqa: E402

MOD, PAQ = ROOT / "modele", ROOT / "paquet_unreal"
DEST = ROOT / "export" / "neutre"
MODELES = ["terrain_sol.glb", "lointain.glb", "route_habillee.glb", "ouvrages.glb", "annexes.glb", "balisage.glb",
           "bati_bord.glb", "village.glb", "clotures.glb", "panneaux_neutres.glb"]
COLLISIONS = {"ouvrages_collision.glb": MOD, "annexes_collision.glb": MOD, "bati_bord_collision.glb": MOD,
              "clotures_collision.glb": MOD,
              "collision.glb": ROOT / "export" / "stage_ir" / "ceyreste",
              "objects_collision.glb": ROOT / "export" / "stage_ir" / "ceyreste"}

# type neutre : (description en clair, substitut libre, nature du substitut)
#   nature : « réel » (modèle redistribuable existant), « forme simple » (à fabriquer : cône, cylindre, cartes
#   croisées, plaque), « projet » (maillage fabriqué par ce projet, fourni dans modeles/), « rien »
TYPES = {
    "pin_alep": ("pin d'Alep (Pinus halepensis), adulte ou jeune selon la hauteur", "forme simple : tronc + houppier en cartes ; "
                 "textures Poly Haven pine_tree_01 (CC0, modèle de 17 M de polygones inutilisable tel quel)", "forme simple"),
    "chene_vert": ("chêne vert (Quercus ilex)", "aucun modèle libre léger connu ; forme simple (houppier rond)", "forme simple"),
    "chene_pubescent": ("chêne pubescent (Quercus pubescens)", "forme simple (houppier rond)", "forme simple"),
    "olivier": ("olivier (Olea europaea)", "aucun modèle libre redistribuable connu (celui du catalogue est sous licence "
                "Fab « Personal ») ; forme simple", "forme simple"),
    "cypres": ("cyprès de Provence (Cupressus sempervirens)", "forme simple (fuseau)", "forme simple"),
    "autre_pin": ("autre pin (pignon ou maritime)", "forme simple", "forme simple"),
    "arbuste_garrigue": ("arbuste de garrigue et de sous-bois (chêne kermès, lentisque, filaire, arbousier ; 0,5 à 6 m)",
                         "Poly Haven wild_rooibos_bush (CC0, buisson approchant)", "réel"),
    "arbuste_bas": ("arbuste bas de garrigue (0,5 à 1,4 m)", "Poly Haven wild_rooibos_bush (CC0)", "réel"),
    "herbe_verte": ("touffe d'herbe verte rase (14 à 32 cm)", "forme simple : cartes croisées, texture Poly Haven "
                    "grass_bermuda_01 (CC0)", "forme simple"),
    "herbe_seche": ("touffe d'herbe sèche (18 à 59 cm)", "forme simple : cartes croisées, texture Poly Haven withered_grass "
                    "(CC0)", "forme simple"),
    "pierre_calcaire": ("pierre calcaire anguleuse (10 cm à 1 m)", "maillage du projet (pierres_calcaires.py), fourni",
                        "projet"),
    "glissiere_simple": ("élément de glissière métallique simple (module 4 m)", "glissière du projet (ouvrages.glb : lisse à "
                         "deux ondes et poteaux), fournie", "projet"),
    "panneau_danger": ("panneau de danger triangulaire (A15b « passage d'animaux sauvages » au PK 86)", "forme simple : plaque "
                       "triangulaire + mât ; face d'après le SVG de la signalisation française (Wikimedia Commons, domaine "
                       "public)", "forme simple"),
    "panneau_virage_droite": ("panneau A1c « succession de virages, le premier à droite » (PK 86)", "forme simple + SVG libre",
                              "forme simple"),
    "balise_virage": ("balise de virage J4 (chevrons blancs sur fond bleu)", "forme simple : plaque + 2 poteaux, SVG libre",
                      "forme simple"),
    "borne_kilometrique": ("borne de point de repère de route départementale (plaquette jaune et blanche)", "forme simple",
                           "forme simple"),
    "poteau_bois": ("poteau électrique ou téléphonique en bois", "forme simple (cylindre de 7 m)", "forme simple"),
    "poteau_beton": ("poteau électrique en béton", "maillage du projet (pierres_calcaires.py), fourni", "projet"),
    "bloc_calcaire": ("bloc calcaire posé (0,4 à 1 m)", "maillage du projet, fourni", "projet"),
    "vehicule": ("véhicule garé (décor)", "rien de libre retenu", "rien"),
    "autre_objet_du_jeu": ("objet du jeu sans description dédiée", "rien", "rien"),
}
ESSENCE = {"pin d'Alep": "pin_alep", "chêne vert": "chene_vert", "chêne pubescent": "chene_pubescent", "olivier": "olivier",
           "cyprès": "cypres", "autre pin (pignon ou maritime)": "autre_pin"}


def type_de(famille, maillage, ligne):
    if ligne.get("essence") in ESSENCE:
        return ESSENCE[ligne["essence"]]
    m = maillage.lower()
    if famille in ("arbustes", "versants") and ("boxthorn" in m or "blackmaple" in m):
        return "arbuste_garrigue"
    if "willow" in m:
        return "arbuste_bas"
    if "greengrass" in m:
        return "herbe_verte"
    if "drygrass" in m or "wildgrass" in m:
        return "herbe_seche"
    if "stone" in m:
        return "pierre_calcaire"
    if "bloc" in m:
        return "bloc_calcaire"
    if "guardrail" in m:
        return "glissiere_simple"
    if "poteaubeton" in m:
        return "poteau_beton"
    if "curvemarker" in m:
        return "balise_virage"
    if "milemarker" in m:
        return "borne_kilometrique"
    if "rightturn" in m:
        return "panneau_virage_droite"
    if "dangera" in m:
        return "panneau_danger"
    if "pylonc" in m:
        return "poteau_bois"
    if "nondrivable" in m:
        return "vehicule"
    if "boxthorn" in m or "blackmaple" in m:
        return "arbuste_garrigue"
    return "autre_objet_du_jeu"


def bornes_glb(path):
    b = path.read_bytes()
    n = struct.unpack("<I", b[12:16])[0]
    j = json.loads(b[20:20 + n])
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for me in j.get("meshes", []):
        for p in me["primitives"]:
            a = j["accessors"][p["attributes"]["POSITION"]]
            if "min" in a:
                lo, hi = np.minimum(lo, a["min"]), np.maximum(hi, a["max"])
    return lo, hi, len(j.get("meshes", [])), len(j.get("images", []))


def main():
    man = json.loads((PAQ / "manifeste.json").read_text(encoding="utf-8"))
    rep = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))["origine"]
    x0, y0, z0 = rep["lambert93_x_m"], rep["lambert93_y_m"], rep["altitude_m"]
    mx = re.findall(r"[-\d.]+", man["repere"]["depuis_lambert93"])
    if shutil.os.path.exists(DEST):
        for sous in ("modeles", "collisions", "placements"):
            shutil.rmtree(DEST / sous, ignore_errors=True)
    for sous in ("modeles", "collisions", "placements"):
        (DEST / sous).mkdir(parents=True, exist_ok=True)
    fichiers = []
    # --- modèles et collisions
    for f in MODELES:
        if (MOD / f).exists():
            shutil.copy(MOD / f, DEST / "modeles" / f)
    if (MOD / "textures_sol").exists():
        shutil.copytree(MOD / "textures_sol", DEST / "modeles" / "textures_sol")
    # maillages fabriqués par le projet, référencés par des instances (pierres, blocs, poteau) : repris du paquet
    for e in man["elements"]:
        if e["type"] == "StaticMesh" and e.get("modele_d_instances"):
            shutil.copy(PAQ / e["fichier"], DEST / "modeles" / Path(e["fichier"]).name)
    for f, d in COLLISIONS.items():
        if (d / f).exists():
            shutil.copy(d / f, DEST / "collisions" / f)
    for sous in ("modeles", "collisions"):
        for p in sorted((DEST / sous).glob("*.glb")):
            lo, hi, nm, ni = bornes_glb(p)
            fichiers.append({"fichier": f"{sous}/{p.name}", "taille_mo": round(p.stat().st_size / 1e6, 2), "maillages": nm,
                             "images_integrees": ni, "bornes_min_m": np.round(lo, 2).tolist(), "bornes_max_m": np.round(hi, 2).tolist()})
    # --- placements des objets du jeu, en clair
    comptes, sources = Counter(), {}
    lignes_par_fam = {}
    for e in man["elements"]:
        if e["type"] != "InstanceGroup":
            continue
        fam = e["fichier"].split("/")[1]
        with open(PAQ / e["fichier"], encoding="utf-8") as f:
            for r in csv.DictReader(f):
                t = type_de(fam, e["maillage_jeu"], r)
                xu, yu, zu = float(r["x_cm"]) / 100, float(r["y_cm"]) / 100, float(r["z_cm"]) / 100
                lac = float(r.get("lacet_deg") or 0.0)
                ech = r.get("echelle") or ""
                lignes_par_fam.setdefault(fam, []).append({
                    "type": t, "x_l93": round(xu + x0, 2), "y_l93": round(y0 - yu, 2), "z_ngf": round(zu + z0, 2),
                    "x_local_m": round(xu, 2), "y_local_haut_m": round(zu, 2), "z_local_sud_m": round(yu, 2),
                    "cap_deg": round((90.0 + lac) % 360.0, 1), "echelle": ech,
                    "hauteur_m": r.get("hauteur_voulue_m", ""), "pk_m": r.get("pk_m", ""),
                    "source": f"{fam} ; ACR {e['maillage_jeu']}"})
                comptes[t] += 1
                sources.setdefault(t, set()).add(e["maillage_jeu"])
    champs = ["type", "x_l93", "y_l93", "z_ngf", "x_local_m", "y_local_haut_m", "z_local_sud_m", "cap_deg", "echelle",
              "hauteur_m", "pk_m", "source"]
    for fam, L in lignes_par_fam.items():
        with open(DEST / "placements" / f"{fam}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=champs); w.writeheader(); w.writerows(L)
    with open(DEST / "correspondance_types.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["type", "description", "maillages_acr", "substitut_libre", "nature_du_substitut", "nombre_place"])
        for t, (desc, sub, nat) in TYPES.items():
            w.writerow([t, desc, " ; ".join(sorted(sources.get(t, []))), sub, nat, comptes.get(t, 0)])
    # --- contrôle
    controle = controler(fichiers, lignes_par_fam, x0, y0, z0)
    taille = sum(p.stat().st_size for p in DEST.rglob("*") if p.is_file())
    manifeste = {
        "format": "export neutre montée de Ceyreste, version 1",
        "date": "2026-11-18",
        "repere": {"origine": {"lambert93_x_m": x0, "lambert93_y_m": y0, "altitude_ngf_m": z0,
                               "description": "axe de la chaussée au PK 0 (ligne de départ estimée)"},
                   "glb": "mètres ; X = est, Y = haut, Z = sud (glTF 2.0, main droite) ; X = x_L93 - x0, Y = z - z0, "
                          "Z = -(y_L93 - y0) ; les sommets sont en coordonnées absolues du repère (aucun nœud transformé)",
                   "vers_unreal": "UE_cm = 100 * (X, Z, Y) : X est, Y sud, Z haut (vérifié pour le paquet ACR par une mire "
                                  "d'axes, voir le manifeste du paquet)",
                   "placements": "x_l93, y_l93 (Lambert-93, EPSG:2154), z_ngf (NGF-IGN69) ; x_local_m, y_local_haut_m, "
                                 "z_local_sud_m dans le repère des glb ; cap_deg : direction de l'axe +X du maillage d'origine, "
                                 "en degrés depuis le nord dans le sens horaire (= 90 + lacet du paquet ACR)"},
        "fichiers": fichiers,
        "placements": {fam: len(L) for fam, L in lignes_par_fam.items()},
        "types": {t: {"nombre": comptes.get(t, 0), "nature_du_substitut": TYPES[t][2]} for t in TYPES},
        "taille_totale_mo": round(taille / 1e6, 1),
        "versionne": ["manifeste.json", "correspondance_types.csv", "controle.json"],
        "regenere": "python scripts/33_export_neutre.py (après 16_paquet_unreal.py)",
        "licences": "géométrie et placements : données IGN (Licence Ouverte Etalab 2.0), relevés du projet ; textures "
                    "Poly Haven CC0 et images IGN ; aucun asset du jeu",
    }
    (DEST / "manifeste.json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")
    (DEST / "controle.json").write_text(json.dumps(controle, ensure_ascii=False, indent=1), encoding="utf-8")
    print("taille", manifeste["taille_totale_mo"], "Mo ;", len(fichiers), "glb ;", sum(comptes.values()), "placements")
    print("verdict :", controle["verdict"], controle["ecarts"][:5])


def controler(fichiers, lignes_par_fam, x0, y0, z0):
    ecarts, mesures = [], {}
    vides = []
    for f in fichiers:
        if not (DEST / f["fichier"]).exists():
            ecarts.append(f"absent : {f['fichier']}")
        elif f["maillages"] == 0:
            vides.append(f["fichier"])            # glb vide (aucun carrefour dessiné à Ceyreste) : pas un écart
        elif not np.isfinite(f["bornes_min_m"]).all():
            ecarts.append(f"bornes illisibles : {f['fichier']}")
    mesures["glb_vides"] = vides
    # emprise : tout dans un carré de 35 km autour de l'origine (lointain jusqu'à l'horizon compris)
    for f in fichiers:
        if f["maillages"] and max(map(abs, f["bornes_min_m"] + f["bornes_max_m"])) > 35000:
            ecarts.append(f"hors emprise : {f['fichier']}")
    if not (DEST / "modeles" / "textures_sol").exists():
        ecarts.append("modeles/textures_sol absent : terrain_sol.glb sans ses images")
    # objets posés : écart au terrain (MNT 0,5 m, à défaut 2 m) ; flottant > 0,3 m, enterré > 0,5 m
    with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as s:
        Z, inv, b = s.read(1).astype(float), ~s.transform, s.bounds
    for fam, L in lignes_par_fam.items():
        x = np.array([r["x_l93"] for r in L]); y = np.array([r["y_l93"] for r in L]); z = np.array([r["z_ngf"] for r in L])
        dans = (x > b.left) & (x < b.right) & (y > b.bottom) & (y < b.top)
        c, l = inv * (x[dans], y[dans])
        zt = map_coordinates(Z, [l - 0.5, c - 0.5], order=1, mode="nearest")
        d = (z[dans] - zt)[zt > -1000]                     # trous du MNT (valeur absente) écartés
        mesures[fam] = {"objets": len(L), "controles": int(dans.sum()),
                        "ecart_au_mnt_m": {"mediane": round(float(np.median(d)), 3) if len(d) else None,
                                           "p1": round(float(np.percentile(d, 1)), 2) if len(d) else None,
                                           "p99": round(float(np.percentile(d, 99)), 2) if len(d) else None},
                        "flottants_sup_0_3_m": int((d > 0.3).sum()), "enterres_sup_0_5_m": int((d < -0.5).sum())}
    alertes = [f"{fam} : {m['flottants_sup_0_3_m']} flottants > 0,3 m et {m['enterres_sup_0_5_m']} enterrés > 0,5 m sur "
               f"{m['controles']}" for fam, m in mesures.items() if isinstance(m, dict) and m.get("controles")]
    return {"verdict": "CONFORME" if not ecarts else "NON CONFORME", "ecarts": ecarts, "alertes": alertes,
            "placements": mesures,
            "note": "Les alertes ne bloquent pas : les objets du paquet sont posés sur le terrain lissé du modèle (terrain_sol.glb), "
                    "pas sur le MNT brut ; un écart de quelques décimètres sur les talus est attendu. controle_paquet.py de carte-reelle-unreal ne s'applique pas (il attend une heightmap de Landscape et "
                    "son manifeste) : contrôle équivalent. Les objets flottants ou enterrés sont mesurés au MNT LiDAR 0,5 m "
                    "nu : un objet posé sur un talus de roche, un mur ou un tablier peut s'en écarter légitimement."}


if __name__ == "__main__":
    main()
