"""Contrôle du semis par secteur (18/11/2026) : densité, hauteur et essences des arbres à moins de 20 m de l'axe, face
au couvert du MNH LiDAR (MNS - MNT > 2 m) du même secteur. Sortie : data/processed/verif_vegetation_secteurs.json.
La lecture des photos Panoramax de chaque secteur est consignée à la main dans docs/03_affinage_reel.md."""
import csv
import collections
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acr_geo import OUT, RAW  # noqa: E402

SECTEURS = [(-140, -30), (60, 235), (250, 450), (500, 700), (850, 950), (1150, 1350), (1500, 1650), (1800, 2000),
            (2150, 2350), (2600, 2800), (3000, 3200)]


def main():
    A = list(csv.DictReader(open(OUT / "arbres.csv", encoding="utf-8")))
    R = list(csv.DictReader(open(OUT / "chaussee_precise.csv", encoding="utf-8")))
    pk = np.array([float(r["pk_m"]) for r in R]); ax = np.array([[float(r["x_axe"]), float(r["y_axe"])] for r in R])
    tg = np.gradient(ax, axis=0); tg /= np.linalg.norm(tg, axis=1)[:, None]; nr = np.c_[tg[:, 1], -tg[:, 0]]
    with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as s1, rasterio.open(RAW / "mns_lidarhd_50cm.tif") as s2:
        T, S, inv = s1.read(1), s2.read(1), ~s1.transform
    off = np.r_[np.arange(-20, -4.5, 1.0), np.arange(5, 20.5, 1.0)]
    out = []
    for a, b in SECTEURS:
        sel = (pk >= a) & (pk <= b)
        X = ax[sel, 0:1] + off[None] * nr[sel, 0:1]; Y = ax[sel, 1:2] + off[None] * nr[sel, 1:2]
        c, l = inv * (X, Y)
        c, l = c.astype(int), l.astype(int)
        h = S[l, c] - T[l, c]
        arb = [r for r in A if a <= float(r["pk_m"]) <= b and float(r["dist_axe_m"]) < 20]
        hs = [float(r["hauteur_m"]) for r in arb]
        ess = collections.Counter(r["essence"] for r in arb)
        out.append({"pk": [a, b], "arbres_a_moins_de_20m_par_100m": round(100 * len(arb) / (b - a), 1),
                     "hauteur_mediane_m": round(float(np.median(hs)), 1) if hs else None,
                     "couvert_mnh_sup_2m_entre_5_et_20m_pct": round(100 * float((h > 2).mean()), 1),
                     "hauteur_mnh_p90_m": round(float(np.percentile(h[h > 2], 90)), 1) if (h > 2).any() else None,
                     "essences_pct": {k: round(100 * v / len(arb)) for k, v in ess.most_common(4)}})
    (OUT / "verif_vegetation_secteurs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for o in out:
        print(o)


if __name__ == "__main__":
    main()
