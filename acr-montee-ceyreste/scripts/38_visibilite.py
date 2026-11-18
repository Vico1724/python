"""Ce qu'un pilote voit depuis la route : bâtiments, murs et clôtures, terrain (demande du 18/11/2026 : « les zones
visibles doivent être vraiment bien faites »).

Positions du pilote : tous les 10 m du PK -150 au PK 3746, œil à 1,1 m au-dessus de la chaussée, sur la voie de droite
dans le sens de la montée, puis sur l'autre voie dans le sens de la descente (redescente en convoi). Champ de vision
retenu : ±70° autour de la direction de la route.
Ligne de vue : rayon de l'œil au point visé (faîtage d'un bâtiment, dessus d'un mur, terrain + 1 m), échantillonné tous
les 1 m jusqu'à 150 m puis tous les 4 m, hors des 3 derniers mètres (l'objet lui-même). Le relief (MNT LiDAR HD 0,5 m
dans le couloir, 2 m au-delà) arrête le rayon s'il passe 0,3 m au-dessus ; la végétation et le bâti (MNS - MNT > 1,5 m)
l'arrêtent après 20 m traversés à moins de 4 m du sol (voir vus()). Le semis du jeu est tiré du même LiDAR : l'écart
avec le jeu est faible mais non nul.
Niveaux : premier plan (vu à moins de 30 m), plan moyen (30 à 150 m), lointain (au-delà), selon la plus courte distance
de vue ; « durée » = mètres de parcours (montée + descente) depuis lesquels l'objet est vu.
Sorties : data/processed/visibilite.json (par bâtiment, par élément de clôture, par cellule de terrain de 20 m),
figures/affinage/visibilite.png
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import map_coordinates

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import FIG, OUT, RAW, REF  # noqa: E402

OEIL_H, PAS, CHAMP = 1.1, 10.0, 70.0
NIVEAUX = ((30.0, "premier_plan"), (150.0, "plan_moyen"), (1e9, "lointain"))


class Raster:
    def __init__(self, f):
        with rasterio.open(f) as s:
            self.a = s.read(1).astype(np.float32); self.inv = ~s.transform; self.b = s.bounds

    def z(self, x, y):
        c, r = self.inv * (np.atleast_1d(np.asarray(x, float)), np.atleast_1d(np.asarray(y, float)))
        return map_coordinates(self.a, [r - 0.5, c - 0.5], order=1, mode="nearest")

    def dedans(self, x, y):
        return (x > self.b.left + 1) & (x < self.b.right - 1) & (y > self.b.bottom + 1) & (y < self.b.top - 1)


class MNS:
    def __init__(self):
        self.f = Raster(RAW / "mns_lidarhd_50cm.tif"); self.g = Raster(RAW / "lointain" / "mns_lidarhd_2m.tif")
        self.tf = Raster(RAW / "mnt_lidarhd_50cm.tif"); self.tg = Raster(RAW / "lointain" / "mnt_lidarhd_2m.tif")

    def _mix(self, a, b, x, y):
        x, y = np.atleast_1d(np.asarray(x, float)), np.atleast_1d(np.asarray(y, float))
        za = a.z(x, y); ok = a.dedans(x, y) & (za > -1000)
        return np.where(ok, za, b.z(x, y))

    def s(self, x, y):
        return self._mix(self.f, self.g, x, y)

    def t(self, x, y):
        return self._mix(self.tf, self.tg, x, y)


def positions():
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as f:
        R = list(csv.DictReader(f))
    pk = np.array([float(r["pk_m"]) for r in R])
    A = np.array([[float(r["x_axe"]), float(r["y_axe"]), float(r["z_axe"])] for r in R])
    out = []
    for p in np.arange(np.ceil(pk[0]), pk[-1], PAS):
        i = int(np.argmin(abs(pk - p)))
        j, k = min(i + 3, len(A) - 1), max(i - 3, 0)
        t = A[j, :2] - A[k, :2]; t /= np.linalg.norm(t)
        dr = np.array([t[1], -t[0]])
        for sens, d, lat in (("montee", t, 1.8), ("descente", -t, -1.8)):
            e = A[i, :2] + dr * lat
            out.append((float(p), sens, e, A[i, 2] + OEIL_H, d))
    return out


def vus(M, eyes, cibles, dmax):
    """cibles : (n, 3) x, y, z visé. Renvoie (n,) distance minimale de vue (inf si jamais vu) et (n,) mètres vus."""
    n = len(cibles)
    dmin = np.full(n, np.inf); duree = np.zeros(n)
    for (p, sens, e, ze, d) in eyes:
        v = cibles[:, :2] - e
        dist = np.hypot(v[:, 0], v[:, 1])
        cos = (v @ d) / np.maximum(dist, 1e-6)
        sel = np.where((dist < dmax) & (dist > 1.0) & (cos > np.cos(np.radians(CHAMP))))[0]
        if not len(sel):
            continue
        for chunk in np.array_split(sel, max(1, len(sel) // 400)):
            D = dist[chunk]
            # échantillons : 1 m jusqu'à 150 m, 4 m au-delà
            s1 = np.arange(1.0, 150.0, 1.0); s2 = np.arange(150.0, dmax, 4.0)
            ss = np.concatenate([s1, s2])
            frac = ss[None, :] / D[:, None]
            garde = (frac < 1.0) & (ss[None, :] < D[:, None] - 3.0)
            X = e[0] + v[chunk, 0:1] * frac; Y = e[1] + v[chunk, 1:2] * frac
            Zr = ze + (cibles[chunk, 2:3] - ze) * frac
            Zs = M.s(X.ravel(), Y.ravel()).reshape(X.shape)
            Zt = M.t(X.ravel(), Y.ravel()).reshape(X.shape)
            # relief (MNT) : bloque dès qu'il passe 0,3 m au-dessus du rayon. Végétation et bâti (MNS - MNT > 1,5 m) :
            # le MNS ne dit pas ce qui est sous les houppiers (le rayon passe sous les pins qui couvrent la route) ;
            # on compte la longueur traversée là où le rayon est à moins de 4 m du sol et sous le sommet de l'objet,
            # et le rayon est arrêté au-delà de 20 m de traversée (sous-bois de kermès et de chênes verts, troncs).
            haut_obj = Zs - Zt; haut_ray = Zr - Zt
            pas_m = np.diff(np.concatenate([np.zeros((len(chunk), 1)), np.broadcast_to(ss, X.shape)], 1), axis=1)
            dense = (haut_obj > 1.5) & (haut_ray < 4.0) & (haut_ray < haut_obj) & garde
            bloque = ((Zt - Zr > 0.3) & garde).any(1) | ((dense * pas_m).sum(1) > 20.0)
            ok = chunk[~bloque]
            dmin[ok] = np.minimum(dmin[ok], dist[ok])
            duree[ok] += PAS / 2          # deux sens par PK : chaque sens compte pour la moitié du pas
    return dmin, duree


def niveau(d):
    for lim, nom in NIVEAUX:
        if d < lim:
            return nom
    return "jamais_vu"


def main():
    M = MNS()
    eyes = positions()
    res = {"methode": __doc__.split("Sorties")[0].strip(), "positions": len(eyes)}
    # --- bâtiments (bilan de 31 : bord de route et village)
    bb = json.loads((OUT / "bati_bilan.json").read_text(encoding="utf-8"))["batiments"]
    import shapely
    from shapely.geometry import shape
    from acr_geo import TO_L93
    poly = {}
    for f in (OUT / "couloir" / "batiment.geojson", OUT / "village" / "batiments_option_a_visibles_du_depart.geojson"):
        for ft in json.loads(Path(f).read_text(encoding="utf-8"))["features"]:
            g = shape(ft["geometry"])
            g = shapely.transform(g, lambda c: np.column_stack(TO_L93.transform(c[:, 0], c[:, 1])))
            poly[str(ft["properties"].get("cleabs"))] = g
    B = [b for b in bb if "pk_m" in b and b["cleabs"] in poly]
    C = []
    for b in B:
        c = np.asarray(poly[b["cleabs"]].centroid.coords[0])
        C.append([c[0], c[1], float(b.get("z_terrain_m") or M.t(*c)[0]) + float(b.get("hauteur_faitage_m", 5.0)) - 0.2])
    C = np.array(C)
    dmin, duree = vus(M, eyes, C, 1500.0)
    bats = []
    for b, d, du in zip(B, dmin, duree):
        bats.append({"cleabs": b["cleabs"], "groupe": b["groupe"], "pk_m": b["pk_m"], "cote": b["cote"],
                     "distance_min_m": None if not np.isfinite(d) else round(float(d), 1), "vu_sur_m": float(du),
                     "niveau": niveau(d), "forme_toit": b.get("forme_toit")})
    res["batiments"] = bats
    res["batiments_par_niveau"] = {k: sum(1 for x in bats if x["niveau"] == k)
                                   for k in ("premier_plan", "plan_moyen", "lointain", "jamais_vu")}
    # --- murs, murets, clôtures (relevé de la troisième passe + parapets des passes 1-2)
    cl = json.loads((REF / "clotures_murets.json").read_text(encoding="utf-8"))["elements"]
    P, ids = [], []
    for e in cl:
        T = np.array(e["trace_l93"], float)
        for q in T[:: max(1, len(T) // max(1, int(len(T) / 5)))]:
            P.append([q[0], q[1], float(M.t(q[0], q[1])[0]) + float(e["hauteur_m"])]); ids.append(e["id"])
    P = np.array(P)
    dmin, duree = vus(M, eyes, P, 400.0)
    par = {}
    for i, d, du in zip(ids, dmin, duree):
        x = par.setdefault(i, [np.inf, 0.0]); x[0] = min(x[0], d); x[1] = max(x[1], du)
    res["clotures"] = [{"id": i, "distance_min_m": None if not np.isfinite(v[0]) else round(float(v[0]), 1),
                        "vu_sur_m": v[1], "niveau": niveau(v[0])} for i, v in par.items()]
    res["clotures_par_niveau"] = {k: sum(1 for x in res["clotures"] if x["niveau"] == k)
                                  for k in ("premier_plan", "plan_moyen", "lointain", "jamais_vu")}
    # --- terrain : cellules de 20 m à moins de 400 m de l'axe
    A = np.array([e[2] for e in eyes])
    x0, y0 = A.min(0) - 400; x1, y1 = A.max(0) + 400
    gx, gy = np.meshgrid(np.arange(x0, x1, 20.0) + 10, np.arange(y0, y1, 20.0) + 10)
    G = np.column_stack([gx.ravel(), gy.ravel()])
    from scipy.spatial import cKDTree
    dd, _ = cKDTree(A).query(G)
    G = G[dd < 400]
    Gz = np.column_stack([G, M.t(G[:, 0], G[:, 1]) + 1.0])
    dmin, duree = vus(M, eyes[::2], Gz, 400.0)
    niv = np.array([niveau(d) for d in dmin])
    res["terrain_cellules_20m"] = {k: int((niv == k).sum()) for k in ("premier_plan", "plan_moyen", "lointain", "jamais_vu")}
    res["terrain_surface_ha"] = {k: round(v * 0.04, 1) for k, v in res["terrain_cellules_20m"].items()}
    (OUT / "visibilite.json").write_text(json.dumps(res, ensure_ascii=False, indent=0), encoding="utf-8")
    # --- figure
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(12, 12))
    col = {"premier_plan": "#c0392b", "plan_moyen": "#e6a23c", "lointain": "#8fb3d9", "jamais_vu": "#dddddd"}
    for k in ("jamais_vu", "lointain", "plan_moyen", "premier_plan"):
        m = niv == k
        ax.scatter(G[m, 0], G[m, 1], s=6, c=col[k], marker="s", lw=0, label=f"terrain : {k} ({m.sum()})")
    ax.plot(A[::2, 0], A[::2, 1], "k-", lw=1)
    for b, c in zip(bats, C):
        ax.scatter(c[0], c[1], s=22, c=col[b["niveau"]], edgecolors="k", linewidths=0.6)
    ax.set_aspect("equal"); ax.set_xlim(A[:, 0].min() - 420, A[:, 0].max() + 420); ax.set_ylim(A[:, 1].min() - 420, A[:, 1].max() + 420)
    ax.set_title("Ce que voit le pilote (montée et descente, œil à 1,1 m, ±70°) — cercles : bâtiments ; carrés : terrain 20 m\n"
                 f"bâtiments : {res['batiments_par_niveau']}", fontsize=10)
    ax.legend(loc="lower right", fontsize=8)
    fig.savefig(FIG / "affinage" / "visibilite.png", dpi=90, bbox_inches="tight")
    print(json.dumps({k: res[k] for k in ("batiments_par_niveau", "clotures_par_niveau", "terrain_surface_ha")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
