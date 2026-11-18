"""Contrôle indépendant du tracé et de la largeur de la chaussée (affinage du 18/11/2026).

Confronte l'axe retenu (data/processed/chaussee_precise.csv, sortie de 07/07b) à :
  - l'axe BD TOPO de la D3 (data/processed/axe_bdtopo_l93.csv) ;
  - l'axe OpenStreetMap de la D3 (Overpass, data/raw/osm/routes.json, téléchargé par ce script s'il manque) ;
  - l'orthophoto 20 cm (RVB + IRC) : bords de l'enrobé visible là où il n'y a pas d'arbre au-dessus (MNS - MNT) ;
  - le LiDAR HD (MNT 0,5 m) : largeur de la plate-forme plane (ce que mesure 07).
Écrit :
  data/processed/verif_trace.csv          une ligne tous les 5 m : écarts BD TOPO / OSM, largeurs
  data/processed/verif_trace.json         bilan chiffré
  data/processed/verif_largeur_points.csv les points de mesure de la largeur (planche à relire)
  figures/affinage/verif_trace.png        écarts latéraux et largeurs le long du parcours
  figures/affinage/verif_largeur_planche.jpg  vignettes d'ortho aux points de mesure, bords dessinés
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acr_geo import FIG, OUT, RAW, l93  # noqa: E402

DFIG = FIG / "affinage"
DFIG.mkdir(parents=True, exist_ok=True)
OSM = RAW / "osm" / "routes.json"
HALF, DT = 9.0, 0.2
T = np.arange(-HALF, HALF + DT / 2, DT)        # t > 0 : à droite dans le sens de la montée


def lire_chaussee():
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as f:
        R = list(csv.DictReader(f))
    g = lambda k: np.array([float(r[k]) for r in R])
    return {k: g(k) for k in ("pk_m", "x_axe", "y_axe", "x_gauche", "y_gauche", "x_droite", "y_droite",
                              "largeur_m")} | {"source": [r["source"] for r in R], "zone": [r["zone"] for r in R]}


def polyligne_osm():
    if not OSM.exists():
        import requests
        OSM.parent.mkdir(parents=True, exist_ok=True)
        q = '[out:json][timeout:90];way["highway"](43.212,5.630,43.240,5.672);out geom tags;'
        for u in ("https://overpass.private.coffee/api/interpreter", "https://overpass-api.de/api/interpreter"):
            try:
                r = requests.post(u, data={"data": q}, timeout=150)
                if r.ok:
                    OSM.write_bytes(r.content); break
            except Exception:
                pass
    d = json.loads(OSM.read_text(encoding="utf-8"))
    segs = []
    for e in d["elements"]:
        if e.get("tags", {}).get("ref") in ("D 3", "D3") and "geometry" in e:
            segs.append(np.array([l93(p["lon"], p["lat"]) for p in e["geometry"]]))
    return segs


def dist_signee(px, py, segs, tx, ty):
    """Écart latéral signé (m, > 0 à droite) du point de l'axe au plus proche segment d'une polyligne."""
    best, sg = math.inf, 0.0
    for s in segs:
        a, b = s[:-1], s[1:]
        ab = b - a
        L2 = (ab ** 2).sum(1); L2[L2 == 0] = 1e-9
        u = np.clip(((px - a[:, 0]) * ab[:, 0] + (py - a[:, 1]) * ab[:, 1]) / L2, 0, 1)
        q = a + u[:, None] * ab
        d = np.hypot(q[:, 0] - px, q[:, 1] - py)
        i = int(np.argmin(d))
        if d[i] < best:
            best = d[i]
            dx, dy = q[i, 0] - px, q[i, 1] - py
            sg = 1.0 if (dx * ty - dy * tx) > 0 else -1.0     # produit vectoriel : à droite de la marche
    return best * sg


def echantillonner(src, xs, ys, bande=None):
    """Valeurs du raster aux points (plus proche voisin), lecture par fenêtre englobante."""
    x0, x1, y0, y1 = xs.min() - 2, xs.max() + 2, ys.min() - 2, ys.max() + 2
    w = from_bounds(x0, y0, x1, y1, src.transform).round_offsets().round_lengths()
    a = src.read(window=w) if bande is None else src.read(bande, window=w)[None]
    tr = src.window_transform(w)
    c = np.floor((xs - tr.c) / tr.a).astype(int); r = np.floor((ys - tr.f) / tr.e).astype(int)
    ok = (r >= 0) & (r < a.shape[1]) & (c >= 0) & (c < a.shape[2])
    out = np.full((a.shape[0],) + xs.shape, np.nan)
    out[:, ok] = a[:, r[ok], c[ok]]
    return out


def bords_image(ndvi, bri, can, ci):
    """Bords de l'enrobé visible sur un profil (indices), None si indécidable (couvert, ombre, contraste)."""
    near = slice(ci - 5, ci + 6)
    if np.nanmax(can[near]) > 1.0:
        return None
    rnd, rbr = np.nanmedian(ndvi[near]), np.nanmedian(bri[near])
    route = (ndvi < rnd + 0.12) & (np.abs(bri - rbr) < max(0.28 * rbr, 22))
    # vote sur 0,6 m
    route = np.convolve(route.astype(float), np.ones(3) / 3, "same") > 0.5
    res = []
    for step in (-1, 1):
        k = ci
        while 0 < k + step < len(route) - 1 and route[k + step]:
            k += step
        if k + step <= 0 or k + step >= len(route) - 1:
            return None
        if can[k + step] > 1.0 or can[min(max(k + 2 * step, 0), len(can) - 1)] > 1.0:
            return None                    # le bord se perd sous un arbre : indécidable
        res.append(k)
    return res


def main():
    C = lire_chaussee()
    pk = C["pk_m"]
    ax = np.c_[C["x_axe"], C["y_axe"]]
    tg = np.gradient(ax, axis=0); tg /= np.linalg.norm(tg, axis=1)[:, None]
    nr = np.c_[tg[:, 1], -tg[:, 0]]                       # normale vers la droite
    # axe BD TOPO
    with open(OUT / "axe_bdtopo_l93.csv", encoding="utf-8") as f:
        bd = np.array([[float(r["x_l93"]), float(r["y_l93"])] for r in csv.DictReader(f)])
    osm = polyligne_osm()
    sel = np.flatnonzero(np.mod(np.round(pk), 5) == 0)
    rows = []
    for i in sel:
        px, py = ax[i]
        rows.append({"pk_m": pk[i], "ecart_bdtopo_m": dist_signee(px, py, [bd], *tg[i]),
                     "ecart_osm_m": dist_signee(px, py, osm, *tg[i]) if osm else np.nan,
                     "largeur_retenue_m": C["largeur_m"][i], "source_07": C["source"][i], "zone": C["zone"][i]})
    # profils image : toutes les stations (1 m)
    Xs = ax[:, 0:1] + T[None] * nr[:, 0:1]; Ys = ax[:, 1:2] + T[None] * nr[:, 1:2]
    with rasterio.open(RAW / "ortho_irc_20cm.tif") as s:
        irc = echantillonner(s, Xs, Ys)
    with rasterio.open(RAW / "ortho_20cm.tif") as s:
        rvb = echantillonner(s, Xs, Ys)
    with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as s:
        mnt = echantillonner(s, Xs, Ys, 1)[0]
    with rasterio.open(RAW / "mns_lidarhd_50cm.tif") as s:
        mns = echantillonner(s, Xs, Ys, 1)[0]
    nir, red = irc[0], irc[1]
    ndvi = (nir - red) / np.maximum(nir + red, 1)
    bri = rvb.mean(0)
    can = mns - mnt
    ci = len(T) // 2
    lg_img = np.full(len(pk), np.nan); bg_img = np.full((len(pk), 2), np.nan)
    for i in range(len(pk)):
        b = bords_image(ndvi[i], bri[i], can[i], ci)
        if b:
            bg_img[i] = T[b[0]] - DT / 2, T[b[1]] + DT / 2
            lg_img[i] = bg_img[i, 1] - bg_img[i, 0]
    # bords retenus (07) en décalage signé
    og = ((np.c_[C["x_gauche"], C["y_gauche"]] - ax) * nr).sum(1)
    od = ((np.c_[C["x_droite"], C["y_droite"]] - ax) * nr).sum(1)
    for r in rows:
        i = int(np.argmin(np.abs(pk - r["pk_m"])))
        r["largeur_image_m"] = lg_img[i]
        r["centre_image_m"] = np.nanmean(bg_img[i]) if np.isfinite(lg_img[i]) else np.nan
    # écart latéral axe retenu / milieu de l'enrobé vu sur l'image
    es = (pk >= 0) & (pk <= 3020)
    vis = np.isfinite(lg_img)
    # points de mesure de la largeur : une vingtaine, répartis, où l'image décide sur ≥ 5 m consécutifs
    from scipy.ndimage import uniform_filter1d
    stable = uniform_filter1d(vis.astype(float), 7) > 0.99
    cand = np.flatnonzero(stable & (pk > -140) & (pk < 3760))
    pts = []
    for cible in np.linspace(-120, 3740, 26):
        if len(cand) == 0:
            break
        j = cand[np.argmin(np.abs(pk[cand] - cible))]
        if abs(pk[j] - cible) < 80 and all(abs(pk[j] - pk[p]) > 60 for p in pts):
            pts.append(j)
    # complète par des points sous couvert (mesure à l'œil sur la planche impossible : notés « couvert »)
    pts_rows = []
    for j in pts:
        sl = slice(max(j - 3, 0), j + 4)
        pts_rows.append({"pk_m": pk[j], "x": ax[j, 0], "y": ax[j, 1],
                         "largeur_image_m": float(np.nanmedian(lg_img[sl])),
                         "largeur_07_m": float(np.median(C["largeur_m"][sl])),
                         "bord_g_image_m": float(np.nanmedian(bg_img[sl, 0])),
                         "bord_d_image_m": float(np.nanmedian(bg_img[sl, 1])),
                         "bord_g_07_m": float(np.median(og[sl])), "bord_d_07_m": float(np.median(od[sl])),
                         "source_07": C["source"][j]})
    with open(OUT / "verif_largeur_points.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(pts_rows[0])); w.writeheader()
        for r in pts_rows:
            w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
    with open(OUT / "verif_trace.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()})
    E = lambda k, m=None: np.array([r[k] for r in rows if (m is None or m(r))], float)
    dans = lambda r: 0 <= r["pk_m"] <= 3020
    def st(v):
        v = v[np.isfinite(v)]
        return {"n": int(len(v)), "mediane": round(float(np.median(np.abs(v))), 2),
                "p95": round(float(np.percentile(np.abs(v), 95)), 2), "max": round(float(np.abs(v).max()), 2),
                "part_sup_0_5_m_pct": round(100 * float((np.abs(v) > 0.5).mean()), 1)} if len(v) else {}
    ci_img = E("centre_image_m", dans)
    bilan = {
        "ecart_axe_retenu_bdtopo_m": st(E("ecart_bdtopo_m", dans)),
        "ecart_axe_retenu_osm_m": st(E("ecart_osm_m", dans)),
        "ecart_axe_retenu_milieu_enrobe_image_m": st(ci_img),
        "ecart_osm_bdtopo_m": st(E("ecart_osm_m", dans) - E("ecart_bdtopo_m", dans)),
        "largeur": {
            "retenue_07_mediane_m": round(float(np.median(C["largeur_m"][es])), 2),
            "image_mediane_m": round(float(np.nanmedian(lg_img[es])), 2),
            "image_part_du_lineaire_pct": round(100 * float(vis[es].mean()), 1),
            "retenue_07_sur_stations_vues_image_m": round(float(np.median(C["largeur_m"][es & vis])), 2),
            "ecart_07_moins_image_median_m": round(float(np.nanmedian((C["largeur_m"] - lg_img)[es & vis])), 2),
            "bdtopo_largeur_de_chaussee_m": "voir troncons_es.csv",
            "points_planche": len(pts_rows),
        },
        "troncons_ecart_bdtopo_sup_0_5_m": [],
    }
    # tronçons où l'axe retenu s'écarte de plus de 0,5 m du milieu de l'enrobé vu sur l'image (≥ 10 m)
    ecart_img = np.nanmean(bg_img, 1)
    m = np.isfinite(ecart_img) & (np.abs(ecart_img) > 0.5)
    m = uniform_filter1d(m.astype(float), 5) > 0.6
    k = 0
    tr = []
    while k < len(m):
        if m[k]:
            j = k
            while j < len(m) and m[j]:
                j += 1
            if pk[j - 1] - pk[k] >= 10:
                tr.append({"pk_debut": float(pk[k]), "pk_fin": float(pk[j - 1]),
                           "ecart_median_m": round(float(np.nanmedian(ecart_img[k:j])), 2)})
            k = j
        else:
            k += 1
    bilan["troncons_axe_hors_milieu_enrobe_image_sup_0_5_m"] = tr
    (OUT / "verif_trace.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    np.save(RAW / "verif_bords_image.npy", np.c_[pk, bg_img, og, od])
    figure(rows, pk, C, lg_img, ecart_img)
    planche(pts_rows, nr, pk)
    print(json.dumps(bilan, ensure_ascii=False, indent=1)[:3000])


def figure(rows, pk, C, lg_img, ecart_img):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    p = np.array([r["pk_m"] for r in rows])
    fig, ax = plt.subplots(3, 1, figsize=(15, 10), sharex=True)
    ax[0].plot(p, [r["ecart_bdtopo_m"] for r in rows], lw=0.9, color="#c0392b", label="axe BD TOPO")
    ax[0].plot(p, [r["ecart_osm_m"] for r in rows], lw=0.9, color="#2471a3", label="axe OpenStreetMap")
    ax[0].plot(pk, ecart_img, ".", ms=1.5, color="#27ae60", label="milieu de l'enrobé, détection automatique (bruitée par les ombres)")
    from acr_geo import REF
    fm = REF / "verif_largeur_ortho_mesures.json"
    mes = json.loads(fm.read_text(encoding="utf-8"))["mesures"] if fm.exists() else []
    if mes:
        ax[0].plot([m["pk_m"] for m in mes if m["axe_peint_m"] is not None],
                   [m["axe_peint_m"] for m in mes if m["axe_peint_m"] is not None], "D", ms=6, color="k",
                   label="axe peint mesuré à l'œil sur l'ortho (repère : axe AVANT affinage)")
    ax[0].axhspan(-0.5, 0.5, color="0.9")
    ax[0].set_ylim(-5, 5); ax[0].set_ylabel("écart à l'axe retenu (m)\n> 0 : à droite")
    ax[0].legend(loc="upper right", fontsize=8); ax[0].grid(alpha=0.3)
    ax[1].plot(pk, C["largeur_m"], lw=0.8, color="0.2", label="largeur retenue (07 : plate-forme LiDAR + ortho)")
    ax[1].plot(pk, lg_img, ".", ms=1.5, color="#27ae60", label="enrobé, détection automatique (bruitée)")
    if mes:
        ax[1].plot([m["pk_m"] for m in mes if m["entre_rives_m"]], [m["entre_rives_m"] for m in mes if m["entre_rives_m"]],
                   "D", ms=6, color="k", label="entre lignes de rive, mesuré à l'œil")
        ax[1].plot([m["pk_m"] for m in mes if m["enrobe_m"]], [m["enrobe_m"] for m in mes if m["enrobe_m"]],
                   "s", ms=6, mfc="none", mec="#d35400", label="enrobé complet, mesuré à l'œil")
    ax[1].set_ylim(3, 12); ax[1].set_ylabel("largeur (m)"); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
    d = C["largeur_m"] - lg_img
    ax[2].plot(pk, d, ".", ms=1.5, color="#8e44ad")
    ax[2].axhline(0, color="k", lw=0.6); ax[2].set_ylim(-3, 4)
    ax[2].set_ylabel("retenue - ortho (m)"); ax[2].set_xlabel("PK (m)"); ax[2].grid(alpha=0.3)
    for a in ax:
        a.axvline(0, color="k", lw=0.5, ls=":"); a.axvline(3000, color="k", lw=0.5, ls=":")
    fig.suptitle("Montée de Ceyreste - contrôle de l'axe et de la largeur (BD TOPO, OSM, ortho 20 cm, LiDAR HD)")
    fig.tight_layout(); fig.savefig(DFIG / "verif_trace.png", dpi=110); plt.close(fig)


def planche(pts_rows, nr, pk):
    from PIL import Image, ImageDraw
    vign = []
    with rasterio.open(RAW / "ortho_20cm.tif") as s:
        for r in pts_rows:
            x, y = r["x"], r["y"]
            w = from_bounds(x - 15, y - 15, x + 15, y + 15, s.transform).round_offsets().round_lengths()
            a = np.moveaxis(s.read(window=w), 0, -1)
            im = Image.fromarray(a).resize((450, 450), Image.LANCZOS)
            dr = ImageDraw.Draw(im)
            i = int(np.argmin(np.abs(pk - r["pk_m"])))
            n = nr[i]
            sc = 450 / 30.0
            def P(t):
                return (225 + t * n[0] * sc, 225 - t * n[1] * sc)
            dr.line([P(-9), P(9)], fill=(255, 255, 255), width=1)
            for t in range(-9, 10):
                q = P(t); dr.ellipse([q[0] - 1.5, q[1] - 1.5, q[0] + 1.5, q[1] + 1.5], fill=(255, 255, 255))
            for t, c in ((r["bord_g_07_m"], (255, 40, 40)), (r["bord_d_07_m"], (255, 40, 40)),
                         (r["bord_g_image_m"], (40, 255, 80)), (r["bord_d_image_m"], (40, 255, 80))):
                q = P(t); dr.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], outline=c, width=2)
            dr.rectangle([0, 0, 450, 34], fill=(0, 0, 0))
            dr.text((6, 3), f"PK {r['pk_m']:.0f}  07: {r['largeur_07_m']:.2f} m  ortho: {r['largeur_image_m']:.2f} m",
                    fill=(255, 255, 255))
            dr.text((6, 18), "rouge = bords 07, vert = bords ortho, points tous les 1 m", fill=(220, 220, 220))
            vign.append(im)
    ncol = 5
    nl = math.ceil(len(vign) / ncol)
    pl = Image.new("RGB", (ncol * 455, nl * 455), (255, 255, 255))
    for k, im in enumerate(vign):
        pl.paste(im, ((k % ncol) * 455, (k // ncol) * 455))
    pl.save(DFIG / "verif_largeur_planche.jpg", quality=85)


if __name__ == "__main__" and "bandes" not in sys.argv:
    main()


def bandes(n_points=24):
    """Bandes d'ortho redressées (route verticale, sens de la montée vers le haut), 20 m de large sur 10 m de long,
    règle tous les 0,5 m, aux points où l'enrobé est dégagé (aucun arbre au-dessus à ±5 m de l'axe sur 10 m) : sert à
    MESURER À L'ŒIL la largeur de l'enrobé (relevé consigné dans data/reference/chaussee_corrections.json)."""
    from PIL import Image, ImageDraw
    C = lire_chaussee()
    pk = C["pk_m"]; ax = np.c_[C["x_axe"], C["y_axe"]]
    tg = np.gradient(ax, axis=0); tg /= np.linalg.norm(tg, axis=1)[:, None]
    nr = np.c_[tg[:, 1], -tg[:, 0]]
    og = ((np.c_[C["x_gauche"], C["y_gauche"]] - ax) * nr).sum(1)
    od = ((np.c_[C["x_droite"], C["y_droite"]] - ax) * nr).sum(1)
    tt = np.arange(-10, 10, 0.1)
    with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as s1, rasterio.open(RAW / "mns_lidarhd_50cm.tif") as s2:
        Xs = ax[:, 0:1] + np.linspace(-4.5, 4.5, 19)[None] * nr[:, 0:1]
        Ys = ax[:, 1:2] + np.linspace(-4.5, 4.5, 19)[None] * nr[:, 1:2]
        can = echantillonner(s2, Xs, Ys, 1)[0] - echantillonner(s1, Xs, Ys, 1)[0]
    libre = np.nanmax(can, 1) < 1.0
    from scipy.ndimage import uniform_filter1d
    libre = uniform_filter1d(libre.astype(float), 7) > 0.99
    cand = np.flatnonzero(libre & (pk > -140) & (pk < 3755))
    pts = []
    for cible in np.linspace(-130, 3750, n_points + 4):
        if len(cand) == 0:
            break
        j = cand[np.argmin(np.abs(pk[cand] - cible))]
        if abs(pk[j] - cible) < 90 and all(abs(pk[j] - pk[p]) > 50 for p in pts):
            pts.append(j)
    vign, meta = [], []
    with rasterio.open(RAW / "ortho_20cm.tif") as s:
        for j in pts:
            ss = np.arange(5, -5, -0.1)                          # haut = vers l'arrivée
            X = ax[j, 0] + ss[:, None] * tg[j, 0] + tt[None] * nr[j, 0]
            Y = ax[j, 1] + ss[:, None] * tg[j, 1] + tt[None] * nr[j, 1]
            a = np.moveaxis(echantillonner(s, X, Y), 0, -1)
            im = Image.fromarray(np.nan_to_num(a).astype(np.uint8)).resize((800, 400), Image.BILINEAR)
            dr = ImageDraw.Draw(im)
            px = lambda t: (t + 10) * 40
            for k in range(-20, 21):
                t = k / 2
                h = 14 if k % 2 == 0 else 7
                dr.line([(px(t), 400 - h), (px(t), 400)], fill=(255, 255, 0), width=1)
                if k % 4 == 0:
                    dr.text((px(t) - 6, 372), f"{int(t)}", fill=(255, 255, 0))
            for t in (og[j], od[j]):
                dr.line([(px(t), 40), (px(t), 70)], fill=(255, 40, 40), width=3)
            dr.rectangle([0, 0, 800, 18], fill=(0, 0, 0))
            dr.text((4, 3), f"#{len(vign)}  PK {pk[j]:.0f}   bords 07 (rouge, en haut) : {og[j]:+.1f} / {od[j]:+.1f}  "
                    f"= {od[j] - og[j]:.2f} m   graduation 0,5 m", fill=(255, 255, 255))
            vign.append(im)
            meta.append({"n": len(meta), "pk_m": round(float(pk[j]), 1), "x": round(float(ax[j, 0]), 2),
                         "y": round(float(ax[j, 1]), 2), "bord_g_07_m": round(float(og[j]), 2),
                         "bord_d_07_m": round(float(od[j]), 2), "largeur_07_m": round(float(od[j] - og[j]), 2),
                         "source_07": C["source"][j]})
    for k in range(0, len(vign), 6):
        pl = Image.new("RGB", (1605, 1215), (255, 255, 255))
        for q, im in enumerate(vign[k:k + 6]):
            pl.paste(im, ((q % 2) * 805, (q // 2) * 405))
        pl.save(DFIG / f"verif_largeur_bandes_{k // 6 + 1}.jpg", quality=88)
    (OUT / "verif_largeur_bandes.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(meta), "bandes")


if __name__ == "__main__" and "bandes" in sys.argv:
    bandes()
