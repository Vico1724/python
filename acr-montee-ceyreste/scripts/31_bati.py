"""Bâti en volumes simples : maisons du bord de la montée et village de Ceyreste vu depuis le départ (option A).

Choix par défaut du 18/11/2026, NON CONFIRMÉ par l'utilisateur (décisions 7 et 8 de docs/ETAT.md) : village en décor
lointain (option A) et maisons du bord de route en volumes simples. Emprise jouable inchangée.

Sources : emprises et hauteurs BD TOPO (data/processed/couloir/batiment.geojson ; data/processed/village/
batiments_option_a_visibles_du_depart.geojson, scripts/28_village.py) ; hauteur du faîtage relue sur le LiDAR HD 0,5 m
(MNS - MNT) là où il existe, BD TOPO ailleurs ; terrain : MNT LiDAR HD 0,5 m, à défaut 2 m (data/raw/lointain).
Forme : murs extrudés et toit à deux pans (faîtage dans l'axe long, pente 30 %, débord 0,3 m) : la fonction
_batiment de 12_carrefours_annexes.py, la même que pour les bâtiments de la zone de départ du Grand Caunet. Matières :
enduit_maison (crépi beige) et tuile (tuiles canal) de 12 ; teintes non mesurées sur les photos (Panoramax 2025 : crépis
beiges et toits de tuiles rouge orangé, cohérents).

Sorties (modele/) :
  bati_bord.glb              maisons à moins de RAYON_BORD_M de l'axe (décor, matières enduit_maison et tuile)
  bati_bord_collision.glb    pavés des façades des maisons à moins de RAYON_COLLISION_M de la chaussée (matière beton,
                             reprise par 09_export_stage_ir.py comme obstacle) ; rien pour le village
  village.glb                village (décor seul, sans collision)
  data/processed/bati_bilan.json  un enregistrement par bâtiment (identifiant BD TOPO stable, PK, distance, hauteur,
                             source de hauteur, visibilité depuis la route)
Noms stables : chaque bâtiment porte l'identifiant BD TOPO (cleabs) ; les maillages sont groupés par matière et par
tronçon de 200 m dans le paquet (16_paquet_unreal.py), noms SM_<niveau>Building_<Matière>_<tronçon>.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import rasterio
import shapely
from scipy.ndimage import map_coordinates
from shapely.geometry import LineString, Polygon, shape

warnings.filterwarnings("ignore")
ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import OUT, RAW, ROOT, TO_L93  # noqa: E402


def charger(nom, f):
    s = importlib.util.spec_from_file_location(nom, ICI / f)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


m12 = charger("m12", "12_carrefours_annexes.py")
import facades as FA  # noqa: E402
RELEVES = ROOT / "data" / "reference" / "facades"   # relevés façade par façade (40_facades.py, quatrième passe)
m11, m08 = m12.m11, m12.m08
MOD = ROOT / "modele"
RAYON_BORD_M = 25.0          # maisons « du bord de route » (demande du 18/11/2026 : les 36 à moins de 25 m de l'axe)
RAYON_COLLISION_M = 15.0     # au-delà, un pilote ne peut pas toucher la façade (talus, clôture, jardin)
PENTE_TOIT = 0.30            # supposé : toits de tuiles canal provençaux (27 à 33 %)


class Relief:
    """MNT 0,5 m là où il existe, 2 m ailleurs ; MNS 0,5 m (None hors emprise)."""
    def __init__(self):
        self.r = []
        for f in (RAW / "mnt_lidarhd_50cm.tif", RAW / "lointain" / "mnt_lidarhd_2m.tif"):
            with rasterio.open(f) as s:
                self.r.append((s.read(1).astype(np.float64), ~s.transform, s.bounds))
        with rasterio.open(RAW / "mns_lidarhd_50cm.tif") as s:
            self.mns = (s.read(1).astype(np.float64), ~s.transform, s.bounds)

    @staticmethod
    def _z(r, x, y):
        a, inv, _ = r
        c, l = inv * (np.asarray(x, float), np.asarray(y, float))
        return map_coordinates(a, [np.asarray(l) - 0.5, np.asarray(c) - 0.5], order=1, mode="nearest")

    def dedans(self, r, x, y, marge=2.0):
        b = r[2]
        x, y = np.asarray(x), np.asarray(y)
        return bool(((x > b.left + marge) & (x < b.right - marge) & (y > b.bottom + marge) & (y < b.top - marge)).all())

    def z(self, x, y):
        for r in self.r:
            if self.dedans(r, x, y):
                z = self._z(r, x, y)
                if (z > -1000).all():
                    return z
        return self._z(self.r[-1], x, y)


class MNTproxy:
    def __init__(self, rel):
        self.rel = rel

    def z(self, x, y):
        return self.rel.z(x, y)


class MNSproxy:
    def __init__(self, rel):
        self.rel = rel

    def z(self, x, y):
        return self.rel._z(self.rel.mns, x, y)


def forme_du_toit(P, rel):
    """« quatre_pans » (croupes) ou « deux_pans », lu sur le LiDAR HD 0,5 m : sur la ligne de faîtage (axe long du
    rectangle minimal), un toit à pignons garde sa hauteur jusqu'à 15 % de la longueur des bouts ; un toit à croupes y
    descend. Retenu « quatre_pans » si les deux bouts sont plus bas que le milieu d'au moins 0,5 m et de 35 % de la
    montée attendue. Renvoie (forme, mesure) ; « deux_pans » hors du LiDAR 0,5 m ou si le toit est masqué (arbres)."""
    if not rel.dedans(rel.mns, *np.asarray(P.exterior.coords).T):
        return "deux_pans", None
    R = np.asarray(P.minimum_rotated_rectangle.exterior.coords)[:4]
    a, b = R[1] - R[0], R[2] - R[1]
    u = a if np.linalg.norm(a) >= np.linalg.norm(b) else b
    Lh = np.linalg.norm(u) / 2; u = u / np.linalg.norm(u); v = np.array([-u[1], u[0]])
    hw = min(np.linalg.norm(a), np.linalg.norm(b)) / 2
    c = R.mean(0)
    if hw < 2.5 or Lh < 3.0:
        return "deux_pans", None

    def h(pt):
        g = np.array([pt + u * du + v * dv for du in (-0.5, 0, 0.5) for dv in (-0.5, 0, 0.5)])
        return float(np.median(rel._z(rel.mns, g[:, 0], g[:, 1]) - rel.z(g[:, 0], g[:, 1])))
    t = Lh * 0.7
    hc, h1, h2 = h(c), h(c + u * t), h(c - u * t)
    attendu = PENTE_TOIT * min(hw, (Lh - t) + hw) if Lh - t < hw else 0.0
    baisse = hc - max(h1, h2)
    mesure = {"faitage_milieu_m": round(hc, 2), "bouts_m": [round(h1, 2), round(h2, 2)]}
    return ("quatre_pans" if baisse > max(0.5, 0.35 * PENTE_TOIT * hw) else "deux_pans"), mesure


def lire(f):
    out = []
    for ft in json.loads(Path(f).read_text(encoding="utf-8"))["features"]:
        g = shape(ft["geometry"])
        g = shapely.transform(g, lambda c: np.column_stack(TO_L93.transform(c[:, 0], c[:, 1])))
        for p in getattr(g, "geoms", [g]):
            if p.geom_type == "Polygon" and p.area > 4.0:
                out.append((ft["properties"], Polygon(np.asarray(p.exterior.coords)[:, :2]).simplify(0.2)))
    return out


def teintes_toits_village(village):
    """Palette de 4 teintes de toit du village, mesurées sur l'ortho IGN 20 cm (médiane de chaque toit, saturation relevée
    comme facades.rgb_releve), et classe de chaque bâtiment (cleabs -> indice). Hors de l'ortho : classe médiane.
    Avant le 19/11/2026, tous les toits avaient la tuile rouge orangé de 12 (sRGB 176, 97, 61) : village trop rouge vu
    de la route (figures/affinage/silhouette/)."""
    import rasterio
    from rasterio.mask import mask
    f = RAW / "ortho_20cm.tif"
    cols = {}
    with rasterio.open(f) as s:
        b = s.bounds
        for p, P in village:
            c = P.centroid
            if not (b.left + 5 < c.x < b.right - 5 and b.bottom + 5 < c.y < b.top - 5):
                continue
            g = P.buffer(-0.6)
            if g.is_empty or g.area < 2:
                continue
            a, _ = mask(s, [g.__geo_interface__], crop=True, filled=False)
            a = a[:3].reshape(3, -1)
            ok = ~np.ma.getmaskarray(a).any(0)
            v = np.asarray(a)[:, ok].T.astype(float)
            if len(v) < 20:
                continue
            lum = v.mean(1)
            garde = (v[:, 1] < v[:, 0] * 1.02) & (lum > np.percentile(lum, 20))
            if garde.sum() < 10:
                continue
            cols[str(p.get("cleabs"))] = np.median(v[garde], 0)
    X = np.array(list(cols.values()))
    # k-moyennes (4 classes), départ déterministe sur les quantiles de clarté
    o = np.argsort(X.mean(1))
    C = X[o[[int(len(o) * q) for q in (0.12, 0.38, 0.62, 0.88)]]].copy()
    for _ in range(30):
        k = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(2), 1)
        C = np.array([X[k == j].mean(0) if (k == j).any() else C[j] for j in range(4)])
    ordre = np.argsort(C.mean(1)); C = C[ordre]
    k = np.argmin(((X[:, None, :] - C[None]) ** 2).sum(2), 1)
    pal = [FA.srgb_hex(FA.rgb_releve({"ortho_rgb": c.tolist()})) for c in C]
    print("palette des toits du village (ortho) :", pal, np.bincount(k, minlength=4).tolist(), "sur", len(village))
    return pal, dict(zip(cols.keys(), k.tolist()))


def main():
    rel = Relief()
    mnt, mns = MNTproxy(rel), MNSproxy(rel)
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    ref = {"x0": ref["origine"]["lambert93_x_m"], "y0": ref["origine"]["lambert93_y_m"], "z0": ref["origine"]["altitude_m"]} \
        if "x0" not in ref else ref
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as f:
        R = list(csv.DictReader(f))
    pk = np.array([float(r["pk_m"]) for r in R])
    axe = LineString([(float(r["x_axe"]), float(r["y_axe"])) for r in R])
    G = np.array([[float(r["x_gauche"]), float(r["y_gauche"])] for r in R])
    D = np.array([[float(r["x_droite"]), float(r["y_droite"])] for r in R])
    ruban = shapely.make_valid(Polygon(np.vstack([G, D[::-1]])))
    A = np.array(axe.coords)
    bord = [(p, P) for p, P in lire(OUT / "couloir" / "batiment.geojson") if P.distance(axe) < RAYON_BORD_M]
    village = lire(OUT / "village" / "batiments_option_a_visibles_du_depart.geojson")
    deja = {p.get("cleabs") for p, _ in bord}
    village = [(p, P) for p, P in village if p.get("cleabs") not in deja and P.distance(axe) > 60]
    palette, teinte_v = teintes_toits_village(village)
    bilan, lots = [], {"bati_bord": [], "village": []}
    coll = []
    for groupe, liste in (("bati_bord", bord), ("village", village)):
        for k, (p, P) in enumerate(sorted(liste, key=lambda t: str(t[0].get("cleabs")))):
            if P.distance(ruban) < 0.5:
                continue                                    # emprise cadastrale qui mord la chaussée : non posée
            c = np.asarray(P.centroid.coords[0])
            dedans05 = rel.dedans(rel.mns, *np.asarray(P.exterior.coords).T)
            h_bd = p.get("hauteur") or p.get("hauteur_bdtopo_m")
            forme, mes_toit = forme_du_toit(P, rel)
            e = {"polygone_l93": np.asarray(P.exterior.coords)[:-1].tolist(), "toit": forme, "pente_toit": PENTE_TOIT,
                 "materiau_murs": "enduit_maison", "materiau_toit": "tuile", "hauteur_bd_topo_m": h_bd,
                 "hauteur_m": None if dedans05 else float(h_bd or 5.5)}
            lot = m12._Lot(ref)
            try:
                cb, inf = m12._batiment(e, lot, mnt, mns, ref)
                if h_bd and inf["hauteur_faitage_m"] > float(h_bd) + 3.0:
                    # faîtage LiDAR plus de 3 m au-dessus de la BD TOPO : arbre ou haie sur le toit (cyprès du PK 3293)
                    e["hauteur_m"] = float(h_bd) + 1.0
                    lot = m12._Lot(ref)
                    cb, inf = m12._batiment(e, lot, mnt, mns, ref)
                    inf["hauteur_methode"] = "BD TOPO + 1 m (MNS - MNT écarté : végétation au-dessus du toit)"
            except Exception as ex:                       # emprise dégénérée (rare) : signalée, non posée
                bilan.append({"cleabs": p.get("cleabs"), "groupe": groupe, "non_pose": str(ex)[:120]})
                continue
            cle = str(p.get("cleabs"))
            fr = RELEVES / f"{cle}.json"
            if fr.exists():
                # bâtiment relevé façade par façade (photos Panoramax 2025) : volumes, toit, ouvertures, volets, génoise…
                # La collision reste celle de _batiment (façades jusqu'à l'égout).
                R = FA.charger_releve(fr)
            if fr.exists() and not R.get("volumes"):
                # façades cachées (mur, haie, arbres) : volume LiDAR gardé, teintes relevées (enduit vu au-dessus du mur,
                # toit sur l'ortho), éléments de toit vus (cheminée)
                ren = {"enduit_maison": f"enduit_{FA.srgb_hex(FA.rgb_releve(R['enduit']))}" if R.get("enduit") else "enduit_maison",
                       "tuile": f"tuile_{FA.srgb_hex(FA.rgb_releve(R['toit']))}" if R.get("toit") else "tuile"}
                lot.parts = {ren.get(k, k): v for k, v in lot.parts.items()}
                inf.update({"releve_facades": fr.relative_to(ROOT).as_posix(), "volumes_releves": 0,
                            "facades_vues": sorted(k for k, f in R.get("facades", {}).items() if f.get("vue"))})
            elif fr.exists():
                lot = m12._Lot(ref)
                Rg = np.asarray(P.exterior.coords)[:-1]
                z0 = float(rel.z(Rg[:, 0], Rg[:, 1]).min())
                B = FA.Batisseur(lot, R, P, FA.faces(P), z0, mnt, detail=R.get("niveau") == "premier_plan")
                cpt = B.construire()
                inf.update({"releve_facades": fr.relative_to(ROOT).as_posix(), "volumes_releves": len(R["volumes"]),
                            **{f"{k}_posees": v for k, v in cpt.items()},
                            "egout_releve_m": [round(z0 + v["egout_z"] - inf["z_terrain_m"], 2) for v in R["volumes"]],
                            "facades_vues": sorted(k for k, f in R["facades"].items() if f.get("vue")),
                            "facades_non_vues": sorted(k for k, f in R["facades"].items() if not f.get("vue"))})
            if groupe == "village":
                # teinte de toit d'après l'ortho IGN 20 cm (classe la plus proche d'une palette de 4 teintes mesurées)
                tv = f"tuile_{palette[teinte_v.get(cle, len(palette) // 2)]}"
                lot.parts = {(tv if k == "tuile" else k): v for k, v in lot.parts.items()}
                inf["teinte_toit"] = tv
            lots[groupe] += lot.meshes(f"{groupe}_{cle}")
            d_ch = float(P.distance(ruban))
            i = int(np.argmin(((A - c) ** 2).sum(1)))
            if groupe == "bati_bord" and d_ch < RAYON_COLLISION_M:
                coll += cb
            bilan.append({"cleabs": cle, "groupe": groupe, "pk_m": float(pk[i]),
                          "cote": "gauche" if (lambda t, v: t[0] * v[1] - t[1] * v[0])(A[min(i + 1, len(A) - 1)] - A[max(i - 1, 0)], c - A[i]) > 0
                          else "droite",
                          "distance_chaussee_m": round(d_ch, 1), "surface_m2": round(P.area, 1),
                          "hauteur_bdtopo_m": h_bd, "collision": groupe == "bati_bord" and d_ch < RAYON_COLLISION_M, **inf,
                          "forme_toit": forme, "forme_toit_mesure_lidar": mes_toit})
    mats = m12.zd_matieres(1024)
    manquants = sorted({m["mat"] for ms in lots.values() for m in ms} - set(mats))
    mats.update(FA.textures(manquants, m11, m12, 512))   # 256 px pour 2 m : 8 mm par pixel
    for groupe, ms in lots.items():
        par = {}
        for m in ms:
            par.setdefault(m["mat"], []).append(m)
        fus = [m11.fusion([{"pos": x["pos"].astype(np.float64), "nrm": x["nrm"], "uv": x["uv"], "idx": x["idx"]} for x in v],
                          f"{groupe}_{mat}", mat) for mat, v in par.items()]
        for f in fus:
            f["pos"] = f["pos"].astype(np.float32)
        m11.ecrire_glb(MOD / f"{groupe}.glb", fus, {k: mats[k] for k in par})
    if coll:
        m11.ecrire_glb(MOD / "bati_bord_collision.glb", [m11.fusion(coll, "bati_bord_beton_collision", "beton")],
                       {"beton": {"color": [0.7, 0.7, 0.68]}})
    # les plus visibles depuis la route : à moins de 8 m de la chaussée, ou plus de 7 m de faîtage à moins de 15 m
    for b in bilan:
        if b.get("groupe") == "bati_bord" and "distance_chaussee_m" in b:
            b["tres_visible"] = b["distance_chaussee_m"] < 8 or (b["distance_chaussee_m"] < 15 and b["hauteur_faitage_m"] > 7)
    resume = {"date": "2026-11-18", "statut": "choix par défaut, non confirmé par l'utilisateur (décisions 7 et 8)",
              "bati_bord_poses": sum(1 for b in bilan if b.get("groupe") == "bati_bord" and "pk_m" in b),
              "bati_bord_avec_collision": sum(1 for b in bilan if b.get("collision")),
              "bati_bord_tres_visibles": sorted([(b["pk_m"], b["cote"], b["cleabs"]) for b in bilan if b.get("tres_visible")]),
              "village_poses": sum(1 for b in bilan if b.get("groupe") == "village" and "pk_m" in b),
              "non_poses": [b for b in bilan if "non_pose" in b],
              "hauteur_lidar": sum(1 for b in bilan if "MNS" in str(b.get("hauteur_methode", ""))),
              "releves_facades": sum(1 for b in bilan if "releve_facades" in b),
              "ouvertures_posees": sum(b.get("ouvertures_posees", 0) for b in bilan),
              "volets_poses": sum(b.get("volets_posees", 0) for b in bilan),
              "elements_poses": sum(b.get("elements_posees", 0) for b in bilan)}
    (OUT / "bati_bilan.json").write_text(json.dumps({"resume": resume, "batiments": bilan}, ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    print(json.dumps(resume, ensure_ascii=False, indent=1)[:2500])


if __name__ == "__main__":
    main()
