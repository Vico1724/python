"""Étape 4 - Profil en long, pentes et inventaire des virages de l'ES.

L'axe BD TOPO (précision planimétrique annoncée 2,5 m) est rééchantillonné tous
les mètres ; l'altitude est lue dans le MNT LiDAR HD à 0,5 m. Les résultats sont
donc une première mesure fiable du relief, et une mesure indicative des rayons :
l'axe sera redessiné sur l'orthophoto et le LiDAR en phase 3.

Sorties (data/processed) :
  profil_es.csv     un point par mètre : PK, position, altitude, pente, cap, rayon
  virages_es.csv    inventaire des virages (PK, sens, rayon mini, angle, catégorie)
  ouvrages_es.csv   ponts et ponceaux franchis (la route y est au-dessus du sol nu)
  synthese_es.json  chiffres clés
"""
import csv
import json

import numpy as np
import rasterio
from scipy.ndimage import map_coordinates
from scipy.signal import savgol_filter

from acr_geo import OUT, RAW, cumdist, load_official, longueur_es, resample, wgs

STEP = 1.0
WIN_Z = 21        # lissage de l'altitude (m) : gomme le bruit, garde bosses et cassures
WIN_XY = 25       # lissage du tracé avant calcul de courbure (m)
R_CORNER = 250.0  # un virage = rayon inférieur à 250 m
MIN_ANGLE = 12.0  # degrés : en dessous, simple inflexion ignorée
GAP = 10          # m : deux arcs de même sens séparés de moins de 10 m = un seul virage
BRIDGE_MARGIN = 15  # m ajoutés de chaque côté d'un ouvrage BD TOPO
# Catégories indicatives (échelle de notes 1 = très serré ... 6 = très rapide)
GRADES = [(15, "épingle"), (25, "1"), (40, "2"), (60, "3"), (90, "4"), (140, "5"), (250, "6")]


def grade(r: float) -> str:
    return next(name for lim, name in GRADES if r <= lim)


def main():
    off = load_official()
    L = longueur_es()                      # PK de l'arrivée ; PK 0 = ligne de départ retenue
    with open(OUT / "axe_bdtopo_l93.csv") as f:
        rows = list(csv.DictReader(f))
    pk0 = float(rows[0]["pk_m"])
    xy = np.array([[float(r["x_l93"]), float(r["y_l93"])] for r in rows])
    s, p = resample(xy, STEP)
    pk = s + pk0

    # altitude LiDAR HD (interpolation bilinéaire dans la grille à 0,5 m)
    with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as src:
        dem = src.read(1)
        inv = ~src.transform
    col, row = inv * (p[:, 0], p[:, 1])
    z_raw = map_coordinates(dem, [np.asarray(row) - 0.5, np.asarray(col) - 0.5], order=1, mode="nearest")
    if (z_raw < -1000).any():
        raise SystemExit("axe hors de l'emprise du MNT")

    # Ponts et ponceaux : le MNT décrit le fond du vallon, pas le tablier. Sur les
    # tronçons que la BD TOPO place « au-dessus du sol », l'altitude de la chaussée
    # est interpolée entre les deux culées.
    spans = []
    with open(OUT / "troncons_es.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["position_par_rapport_au_sol"] == "1":
                a = float(r["pk_debut_m"])
                b = a + float(r["longueur_m"])
                if spans and a - spans[-1][1] < 2 * BRIDGE_MARGIN:
                    spans[-1][1] = b
                else:
                    spans.append([a, b])
    z_road, bridges = z_raw.copy(), []
    for a, b in spans:
        i0 = max(int(np.searchsorted(pk, a - BRIDGE_MARGIN)), 3)
        i1 = min(int(np.searchsorted(pk, b + BRIDGE_MARGIN)), len(pk) - 4)
        za, zb = z_raw[i0 - 3:i0].mean(), z_raw[i1:i1 + 3].mean()
        deck = np.interp(pk[i0:i1], [pk[i0], pk[i1]], [za, zb])
        depth = float((deck - z_raw[i0:i1]).max())
        z_road[i0:i1] = np.maximum(z_raw[i0:i1], deck)
        k = i0 + int(np.argmax(deck - z_raw[i0:i1]))
        lon, lat = wgs(p[k, 0], p[k, 1])
        bridges.append({"pk_debut_m": round(a), "pk_fin_m": round(b), "longueur_bdtopo_m": round(b - a, 1),
                        "hauteur_sous_tablier_m": round(depth, 1), "altitude_chaussee_m": round(float(deck.mean()), 1),
                        "lat": round(lat, 6), "lon": round(lon, 6), "dans_es": bool(0 <= a <= L)})
    with open(OUT / "ouvrages_es.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(bridges[0]))
        w.writeheader()
        w.writerows(bridges)
    z = savgol_filter(z_road, WIN_Z, 2)
    slope = np.gradient(z, s) * 100.0

    # courbure sur l'axe lissé
    xs, ys = (savgol_filter(p[:, k], WIN_XY, 2) for k in (0, 1))
    dx, dy = np.gradient(xs, s), np.gradient(ys, s)
    ddx, ddy = np.gradient(dx, s), np.gradient(dy, s)
    kappa = (dx * ddy - dy * ddx) / np.maximum((dx * dx + dy * dy) ** 1.5, 1e-9)   # + = gauche
    heading = (np.degrees(np.arctan2(dx, dy)) + 360) % 360                          # 0 = nord
    radius = np.where(np.abs(kappa) > 1e-5, 1 / np.maximum(np.abs(kappa), 1e-5), np.inf)

    with open(OUT / "profil_es.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pk_m", "x_l93", "y_l93", "lon", "lat", "z_sol_lidar_m", "z_chaussee_m", "pente_pct",
                    "cap_deg", "rayon_m", "sens"])
        for i in range(len(s)):
            lon, lat = wgs(p[i, 0], p[i, 1])
            r = radius[i]
            w.writerow([round(pk[i], 1), round(p[i, 0], 2), round(p[i, 1], 2), round(lon, 7), round(lat, 7),
                        round(float(z_raw[i]), 2), round(float(z[i]), 2), round(float(slope[i]), 2),
                        round(float(heading[i]), 1), "" if r > 2000 else round(float(r)),
                        "" if r > R_CORNER else ("G" if kappa[i] > 0 else "D")])

    # --- virages : plages contiguës de même sens sous le rayon seuil ----------
    stage = (pk >= 0) & (pk <= L)
    sign = np.where(np.abs(kappa) > 1 / R_CORNER, np.sign(kappa), 0).astype(int)
    idx = np.flatnonzero(sign)
    for a, b in zip(idx[:-1], idx[1:]):          # comble les courtes interruptions
        if 1 < b - a <= GAP and sign[a] == sign[b]:
            sign[a:b] = sign[a]
    corners, i = [], 0
    while i < len(sign):
        if sign[i] == 0:
            i += 1
            continue
        j = i
        while j + 1 < len(sign) and sign[j + 1] == sign[i]:
            j += 1
        angle = float(np.degrees(np.abs(kappa[i:j + 1]).sum() * STEP))
        if angle >= MIN_ANGLE:
            k = i + int(np.argmin(radius[i:j + 1]))
            rmin = float(radius[k])
            corners.append({"pk_debut_m": round(pk[i]), "pk_corde_m": round(pk[k]), "pk_fin_m": round(pk[j]),
                            "sens": "gauche" if sign[i] > 0 else "droite", "rayon_mini_m": round(rmin),
                            "angle_deg": round(angle), "longueur_m": round(pk[j] - pk[i] + STEP),
                            "categorie": grade(rmin), "pente_pct": round(float(slope[k]), 1),
                            "dans_es": bool(0 <= pk[k] <= L)})
        i = j + 1
    for n, c in enumerate(corners, 1):
        c["n"] = n
    with open(OUT / "virages_es.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["n", *[k for k in corners[0] if k != "n"]])
        w.writeheader()
        w.writerows(corners)

    # --- synthèse -------------------------------------------------------------
    zs, ss = z[stage], s[stage]
    d3 = float(np.sqrt(np.diff(ss) ** 2 + np.diff(zs) ** 2).sum())
    dz = np.diff(zs)
    inside = [c for c in corners if c["dans_es"]]
    straight, prev = [], 0.0
    for c in inside:
        straight.append((c["pk_debut_m"] - prev, prev, c["pk_debut_m"]))
        prev = c["pk_fin_m"]
    straight.append((L - prev, prev, L))
    longest = max(straight)
    widths = {}
    with open(OUT / "troncons_es.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            a, ln = float(r["pk_debut_m"]), float(r["longueur_m"])
            inside_len = max(0.0, min(a + ln, L) - max(a, 0.0))
            if inside_len > 0:
                key = f'{r["cpx_numero"]} - {r["largeur_de_chaussee"]} m'
                widths[key] = round(widths.get(key, 0) + inside_len)
    by_grade = {}
    for c in inside:
        by_grade[c["categorie"]] = by_grade.get(c["categorie"], 0) + 1
    tight = min(inside, key=lambda c: c["rayon_mini_m"])
    over = float((np.abs(slope[stage]) > 12).mean() * 100)
    summary = {
        "longueur_officielle_m": off["longueur_officielle_km"] * 1000,
        "longueur_entre_lignes_axe_bdtopo_m": L,
        "longueur_3d_mesuree_m": round(d3, 1),
        "altitude_depart_m": round(float(zs[0]), 1),
        "altitude_arrivee_m": round(float(zs[-1]), 1),
        "altitude_max_m": round(float(zs.max()), 1),
        "pk_altitude_max_m": round(float(pk[stage][zs.argmax()])),
        "altitude_min_m": round(float(zs.min()), 1),
        "pk_altitude_min_m": round(float(pk[stage][zs.argmin()])),
        "denivele_positif_m": round(float(dz[dz > 0].sum())),
        "denivele_negatif_m": round(float(-dz[dz < 0].sum())),
        "pente_moyenne_pct": round(float((zs[-1] - zs[0]) / L * 100), 2),
        "pente_max_montee_pct": round(float(slope[stage].max()), 1),
        "pente_max_descente_pct": round(float(slope[stage].min()), 1),
        "part_du_parcours_pente_sup_12pct": round(over, 2),
        "nombre_virages": len(inside),
        "virages_par_categorie": dict(sorted(by_grade.items())),
        "virage_le_plus_serre": {k: tight[k] for k in ("n", "pk_corde_m", "sens", "rayon_mini_m", "angle_deg")},
        "plus_longue_portion_sans_virage_m": {"longueur": round(longest[0]), "de_pk": round(longest[1]),
                                              "a_pk": round(longest[2])},
        "largeur_chaussee_bdtopo_m_par_longueur": widths,
        "ouvrages_dans_es": sum(b["dans_es"] for b in bridges),
        "ecart_moyen_lissage_altitude_cm": round(float(np.abs(z_road - z)[stage].mean() * 100), 1),
        "avertissement": "rayons et catégories indicatifs (axe BD TOPO, précision 2,5 m) ; à affiner en phase 3",
    }
    (OUT / "synthese_es.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
