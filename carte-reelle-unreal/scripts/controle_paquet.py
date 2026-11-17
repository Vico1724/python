"""Contrôle d'un paquet carte-reelle-unreal : verdict CONFORME / NON CONFORME et liste des écarts.

Vérifie, sans Unreal ni téléchargement :
  - manifeste lisible, fichiers listés présents avec la taille annoncée ;
  - heightmap : PNG 16 bits carré d'une taille de Landscape valide, plage utilisée, pas de grand
    aplat aux valeurs extrêmes (trou bouché), RAW identique, échelles Unreal cohérentes avec le
    pas et les altitudes ;
  - texture du terrain : carrée, au plus 8192 px, peu de pixels vides ;
  - maillages glb : bornes lues dans le fichier = bornes du manifeste ; terrain proche = carré du
    Landscape ; lointain qui l'entoure ; bâtiments et routes dans la zone de détail ;
  - altitudes plausibles, z0 entre min et max ; arbres dans la zone, au sol, hauteurs et rayons
    plausibles ; comptes d'objets ; types d'arbres présents dans table_assets.csv.
Écarts bloquants -> NON CONFORME (code de sortie 1) ; les avertissements n'empêchent pas CONFORME.

Usage : python controle_paquet.py --sortie DOSSIER   (paquet = DOSSIER/paquet_unreal)
        python controle_paquet.py --paquet DOSSIER_DU_PAQUET
Sorties : verdict (1 à 5 lignes), détails dans <paquet>/controle.json
"""
import argparse
import csv
import json
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image

TAILLES_LANDSCAPE = (505, 1009, 2017, 4033, 8129)
ALT_MIN, ALT_MAX = -450.0, 8850.0     # mer Morte, Everest : hors de cette plage l'altitude est fausse
APLAT_MAX = 0.05                      # part maximale de pixels à 0 ou 65535 (au-delà : trou ou écrêtage)
VIDE_MAX = 5.0                        # % de pixels vides tolérés dans la texture du terrain
TOL_BORNES_CM = 1.0                   # arrondi des bornes du manifeste (0,1 cm) et du flottant 32 bits
MARGE_OBJETS_M = 25.0                 # demi-largeur de route ou débord toléré hors de la zone de détail

Image.MAX_IMAGE_PIXELS = None
for _flux in (sys.stdout, sys.stderr):      # tube en cp1252 sous Windows : pas d'échec sur « ≠ » ou « ≤ »
    try:
        _flux.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass


class Controle:
    def __init__(self):
        self.bloquants, self.avertissements, self.mesures = [], [], {}

    def exige(self, ok, msg):
        if not ok:
            self.bloquants.append(msg)
        return ok

    def signale(self, ok, msg):
        if not ok:
            self.avertissements.append(msg)
        return ok


def bornes_glb(chemin: Path):
    """Bornes Unreal (cm) d'un .glb, d'après le min/max des accesseurs POSITION (sans transformations de nœuds)."""
    b = chemin.read_bytes()
    if b[:4] != b"glTF":
        raise ValueError("pas un fichier glb")
    n = struct.unpack_from("<I", b, 12)[0]
    doc = json.loads(b[20:20 + n])
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for nd in doc.get("nodes", []):
        if any(k in nd for k in ("matrix", "translation", "rotation", "scale")):
            m = nd.get("matrix")
            ident = m is None or np.allclose(m, np.eye(4).ravel())
            if not ident or nd.get("translation") or nd.get("rotation") or nd.get("scale"):
                raise ValueError("nœud transformé : contrôle des bornes impossible")
    tri = 0
    for mesh in doc.get("meshes", []):
        for p in mesh["primitives"]:
            acc = doc["accessors"][p["attributes"]["POSITION"]]
            lo, hi = np.minimum(lo, acc["min"]), np.maximum(hi, acc["max"])
            if "indices" in p:
                tri += doc["accessors"][p["indices"]]["count"] // 3
    ue = lambda v: [v[0] * 100, v[2] * 100, v[1] * 100]
    return {"min": ue(lo), "max": ue(hi)}, tri


def lire_csv(p: Path):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def controler(P: Path) -> Controle:
    C = Controle()
    pm = P / "manifeste.json"
    if not C.exige(pm.exists(), f"manifeste.json absent de {P}"):
        return C
    man = json.loads(pm.read_text(encoding="utf-8"))
    C.exige(man.get("format", "").startswith("carte-reelle-unreal/"), "format de manifeste inconnu")

    # --- fichiers
    for f in man["fichiers"]:
        p = P / f["chemin"]
        if C.exige(p.exists(), f"fichier manquant : {f['chemin']}"):
            C.exige(p.stat().st_size > 0, f"fichier vide : {f['chemin']}")
            if f["chemin"] not in ("manifeste.json", "LISEZMOI_import.md"):
                C.signale(p.stat().st_size == f["octets"], f"taille différente du manifeste : {f['chemin']}")
    C.mesures["fichiers"] = len(man["fichiers"])

    # --- repère et altitudes
    rep, alt, L = man["repere"], man["altitudes_m"], man["landscape"]
    C.exige(ALT_MIN <= alt["min"] <= alt["max"] <= ALT_MAX, f"altitudes implausibles : {alt}")
    C.exige(rep["z0_m"] is not None and alt["min"] - 0.01 <= rep["z0_m"] <= alt["max"] + 0.01,
            f"z0 {rep['z0_m']} hors de [{alt['min']}, {alt['max']}]")
    C.signale(alt["max"] - alt["min"] < 3000, f"dénivelé de {alt['max'] - alt['min']:.0f} m sur la zone : à vérifier")

    # --- heightmap
    hm = P / L["fichier"]
    n, pas = L["taille_px"], L["pas_m"]
    if C.exige(hm.exists(), "heightmap absente"):
        im = Image.open(hm)
        a = np.asarray(im).astype(np.int64)
        C.exige(im.mode in ("I;16", "I;16B", "I") and a.max() <= 65535, f"heightmap pas en 16 bits (mode {im.mode})")
        C.exige(a.shape == (n, n), f"heightmap {a.shape} au lieu de {n} x {n}")
        C.exige(n in TAILLES_LANDSCAPE, f"taille {n} non valide pour un Landscape ({TAILLES_LANDSCAPE})")
        C.exige(a.min() == 0 and a.max() == 65535, f"plage de la heightmap non utilisée ({a.min()} à {a.max()})")
        aplat = max((a == 0).mean(), (a == 65535).mean())
        C.exige(aplat <= APLAT_MAX, f"{aplat * 100:.1f} % de la heightmap à une valeur extrême : trou ou écrêtage")
        C.signale(len(np.unique(a)) > 50, "heightmap presque plate (moins de 50 niveaux)")
        r16 = hm.with_suffix(".r16")
        if r16.exists():
            C.exige(np.array_equal(np.fromfile(r16, "<u2").astype(np.int64), a.ravel()), "RAW .r16 différent du PNG")
        C.mesures["heightmap"] = {"taille": n, "valeurs": [int(a.min()), int(a.max())], "niveaux": int(len(np.unique(a)))}
    plage = L["z_max_m"] - L["z_min_m"]
    e = L["echelle_cm"]
    C.exige(abs(e["x"] - pas * 100) < 1e-6 and abs(e["y"] - pas * 100) < 1e-6, "échelle X/Y ≠ pas du terrain")
    C.exige(abs(e["z"] - plage * 12800 / 65535) < 1e-3, "échelle Z incohérente avec la plage d'altitude")
    pz = L["z_min_m"] * 100 + 32768 / 65535 * plage * 100
    C.exige(abs(L["position_centre_cm"][2] - pz) < 0.1, "position Z du Landscape incohérente")
    C.exige(abs(L["z_min_m"] + rep["z0_m"] - alt["min"]) < 0.05, "z_min du Landscape ≠ altitude min - z0")
    demi = (n - 1) * pas / 2
    C.exige(L["bornes_locales"] == [-demi, -demi, demi, demi], "bornes du Landscape ≠ taille x pas")

    # --- texture du terrain
    tex = P / L["texture"]
    if C.exige(tex.exists(), "texture du terrain absente"):
        t = np.asarray(Image.open(tex).convert("RGB"))
        C.exige(t.shape[0] == t.shape[1] and t.shape[0] <= 8192, f"texture {t.shape[1]} x {t.shape[0]} : carrée et ≤ 8192 attendue")
        s = t.astype(np.int16).sum(axis=2)
        vide = float(((s == 0) | (s == 765)).mean() * 100)
        C.exige(vide <= VIDE_MAX, f"texture du terrain vide à {vide:.1f} %")
        C.mesures["texture"] = {"px": t.shape[0], "vide_pct": round(vide, 2)}

    # --- maillages
    bd = man["bornes_detail_locales"]
    C.mesures["maillages"] = {}
    roles = {}
    for m in man["maillages"]:
        p = P / m["fichier"]
        if not C.exige(p.exists(), f"maillage absent : {m['fichier']}"):
            continue
        try:
            b, tri = bornes_glb(p)
        except Exception as ex:
            C.exige(False, f"{m['fichier']} illisible : {ex}")
            continue
        ecart = max(abs(x - y) for x, y in zip(b["min"] + b["max"], m["bornes_cm"]["min"] + m["bornes_cm"]["max"]))
        C.exige(ecart <= TOL_BORNES_CM, f"{m['fichier']} : bornes du fichier ≠ manifeste (écart {ecart:.1f} cm)")
        C.exige(tri > 0, f"{m['fichier']} sans triangle")
        roles[m["role"]] = b
        C.mesures["maillages"][m["role"]] = {"triangles": tri, "bornes_cm": b}
    cm = lambda v: v * 100
    if "terrain_proche" in roles:
        b = roles["terrain_proche"]
        C.exige(abs(b["min"][0] - cm(-demi)) < 1 and abs(b["max"][0] - cm(demi)) < 1 and abs(b["min"][1] - cm(-demi)) < 1
                and abs(b["max"][1] - cm(demi)) < 1, "terrain_proche.glb ne couvre pas exactement le Landscape")
        C.signale(abs(b["min"][2] - cm(L["z_min_m"])) < 200 and abs(b["max"][2] - cm(L["z_max_m"])) < 200,
                  "altitudes du terrain proche éloignées de celles du Landscape (> 2 m)")
    if "lointain" in roles:
        b = roles["lointain"]
        C.exige(b["min"][0] <= cm(-demi) and b["max"][0] >= cm(demi) and b["min"][1] <= cm(-demi) and b["max"][1] >= cm(demi),
                "le lointain n'entoure pas le Landscape")
    for r in ("batiments", "routes"):
        if r in roles:
            b = roles[r]
            ok = (b["min"][0] >= cm(bd[0] - MARGE_OBJETS_M) and b["max"][0] <= cm(bd[2] + MARGE_OBJETS_M)
                  and b["min"][1] >= cm(-bd[3] - MARGE_OBJETS_M) and b["max"][1] <= cm(-bd[1] + MARGE_OBJETS_M))
            C.exige(ok, f"{r}.glb déborde de la zone de détail")
            C.exige(b["min"][2] >= cm(L["z_min_m"] - 5) and b["min"][2] <= cm(L["z_max_m"] + 5),
                    f"{r}.glb : base hors des altitudes du terrain")

    # --- placements
    pl = man["placements"]
    pa = P / pl["arbres"]["fichier"]
    if pa.exists():
        arbres = lire_csv(pa)
        C.exige(list(arbres[0].keys()) == ["x", "y", "z", "hauteur", "rayon", "type"] if arbres else True,
                "colonnes de arbres.csv inattendues")
        C.exige(len(arbres) == pl["arbres"]["nombre"], "nombre d'arbres ≠ manifeste")
        C.signale(len(arbres) > 0, "aucun arbre (zone sans végétation ?)")
        if arbres:
            x, y, z, h, r = (np.array([float(a[k]) for a in arbres]) for k in ("x", "y", "z", "hauteur", "rayon"))
            dedans = (x >= bd[0] - 1) & (x <= bd[2] + 1) & (y >= bd[1] - 1) & (y <= bd[3] + 1)
            C.exige(dedans.all(), f"{(~dedans).sum()} arbres hors de la zone de détail")
            sol = (z >= L["z_min_m"] - 2) & (z <= L["z_max_m"] + 2)
            C.exige(sol.mean() >= 0.99, f"{(~sol).sum()} arbres hors des altitudes du terrain")
            C.exige(((h >= 0.3) & (h <= 90)).all(), f"hauteurs d'arbres implausibles ({h.min():.1f} à {h.max():.1f} m)")
            C.exige(((r >= 0.1) & (r <= 30)).all(), f"rayons d'arbres implausibles ({r.min():.1f} à {r.max():.1f} m)")
            types = {a["type"] for a in arbres}
            tbl = P / "table_assets.csv"
            if tbl.exists():
                connus = {t["type"] for t in lire_csv(tbl) if (t.get("asset") or "").strip()}
                C.signale(types <= connus, f"types sans asset dans table_assets.csv : {sorted(types - connus)}")
            C.mesures["arbres"] = {"nombre": len(arbres), "hauteur_max": float(h.max()), "types": len(types)}
    else:
        C.signale(False, "pas de placements/arbres.csv (étape 05 non faite)")
    for k in ("batiments", "routes"):
        p = P / pl[k]["fichier"]
        if C.exige(p.exists(), f"{pl[k]['fichier']} absent"):
            d = json.loads(p.read_text(encoding="utf-8"))[k]
            C.exige(len(d) == pl[k]["nombre"], f"nombre de {k} ≠ manifeste")
            C.signale(len(d) > 0, f"aucun objet dans {k}")
            C.mesures[k] = len(d)
    if (P / "placements" / "batiments.json").exists():
        bats = json.loads((P / "placements" / "batiments.json").read_text(encoding="utf-8"))["batiments"]
        hb = [b["hauteur_m"] for b in bats]
        C.exige(all(1 <= v <= 400 for v in hb), "hauteurs de bâtiments implausibles")
    return C


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sortie", help="dossier de travail de la zone (paquet = <sortie>/paquet_unreal)")
    ap.add_argument("--paquet", help="dossier du paquet")
    ap.add_argument("--zone", help="ignoré (accepté pour garder les mêmes arguments que les autres étapes)")
    a = ap.parse_args()
    if not (a.sortie or a.paquet):
        ap.error("--sortie ou --paquet")
    P = Path(a.paquet or Path(a.sortie) / "paquet_unreal").resolve()
    C = controler(P)
    verdict = "CONFORME" if not C.bloquants else "NON CONFORME"
    (P / "controle.json").write_text(json.dumps({"verdict": verdict, "ecarts_bloquants": C.bloquants,
                                                 "avertissements": C.avertissements, "mesures": C.mesures},
                                                ensure_ascii=False, indent=1, default=float), encoding="utf-8") if P.exists() else None
    m = C.mesures
    lignes = [f"controle_paquet : {verdict} ({len(C.bloquants)} écart(s) bloquant(s), {len(C.avertissements)} avertissement(s)) ; "
              f"heightmap {m.get('heightmap', {}).get('taille', '?')}, {m.get('arbres', {}).get('nombre', 0)} arbres, "
              f"{m.get('batiments', 0)} bâtiments, {m.get('routes', 0)} routes"]
    lignes += [f"  ÉCART : {e}" for e in C.bloquants[:3]]
    lignes += [f"  avertissement : {e}" for e in C.avertissements[:4 - min(3, len(C.bloquants))]]
    print("\n".join(lignes[:5]))
    sys.exit(0 if not C.bloquants else 1)


if __name__ == "__main__":
    main()
