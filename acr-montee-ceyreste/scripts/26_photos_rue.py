"""Imagerie de rue Panoramax le long de la montée (et du village) : inventaire, téléchargement, vues planes.

Source : Panoramax, méta-catalogue https://api.panoramax.xyz/api (API STAC, sans clé). Licence lue image par
image (`properties.license`) ; producteur = `geovisio:producer`. Les images ne sont PAS versionnées : elles vont
dans data/raw/panoramax/ (ignoré par git). Seule la liste (identifiant, position, date, licence, URL) est versionnée,
dans data/reference/photos_rue_panoramax.csv.

Usage :
  python scripts/26_photos_rue.py inventaire          liste des images à moins de 25 m de l'axe (PK -150 à 3768)
  python scripts/26_photos_rue.py telecharger [--pas 20]  télécharge les images HD retenues (une tous les --pas m
                                                       par sens) et en tire des vues planes (avant, gauche, droite)
  python scripts/26_photos_rue.py vue ID CAP [FOV] [LARGEUR]  une vue plane d'une image téléchargée (cap absolu, °)
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acr_geo import OUT, RAW, REF, l93, _session  # noqa: E402

API = "https://api.panoramax.xyz/api/search"
DOSSIER = RAW / "panoramax"
LISTE = REF / "photos_rue_panoramax.csv"
CHAMPS = ["id", "collection", "pk_m", "ecart_m", "x_l93", "y_l93", "lon", "lat", "azimut_deg", "sens", "date",
          "producteur", "licence", "url_hd", "url_sd", "camera", "fov_deg"]


def axe():
    pk, x, y = [], [], []
    with open(OUT / "chaussee_precise.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            pk.append(float(r["pk_m"])); x.append(float(r["x_axe"])); y.append(float(r["y_axe"]))
    return np.array(pk), np.array(x), np.array(y)


def projeter(pk, x, y, px, py):
    d2 = (x - px) ** 2 + (y - py) ** 2
    i = int(np.argmin(d2))
    j = min(i + 1, len(x) - 1); k = max(i - 1, 0)
    tx, ty = x[j] - x[k], y[j] - y[k]
    n = math.hypot(tx, ty) or 1.0
    tx, ty = tx / n, ty / n
    lat = (px - x[i]) * (-ty) + (py - y[i]) * tx          # > 0 : à gauche dans le sens de la montée
    cap = math.degrees(math.atan2(tx, ty)) % 360
    return float(pk[i]), float(lat), cap


def inventaire(bbox_extra=None):
    pk, x, y = axe()
    from acr_geo import wgs
    vus = {}
    # Boîtes de 250 m le long de l'axe (la recherche plafonne à 100 résultats par page).
    for i in range(0, len(pk), 200):
        sx, sy = x[i:i + 200], y[i:i + 200]
        x0, y0, x1, y1 = sx.min() - 30, sy.min() - 30, sx.max() + 30, sy.max() + 30
        lo0, la0 = wgs(x0, y0); lo1, la1 = wgs(x1, y1)
        url, params = API, {"bbox": f"{lo0},{la0},{lo1},{la1}", "limit": 100}
        while url:
            r = _session.get(url, params=params, timeout=60); r.raise_for_status()
            d = r.json()
            for f in d.get("features", []):
                vus[f["id"]] = f
            nxt = [l for l in d.get("links", []) if l.get("rel") == "next"]
            url, params = (nxt[0]["href"], None) if nxt else (None, None)
    lignes = []
    for fid, f in vus.items():
        lon, lat = f["geometry"]["coordinates"][:2]
        px, py = l93(lon, lat)
        p, ecart, cap_route = projeter(pk, x, y, px, py)
        if abs(ecart) > 25 or p <= pk[0] + 1 or p >= pk[-1] - 1:
            continue
        pr = f["properties"]
        az = pr.get("view:azimuth")
        sens = ""
        if az is not None:
            dif = (float(az) - cap_route + 540) % 360 - 180
            sens = "montant" if abs(dif) < 60 else ("descendant" if abs(dif) > 120 else "travers")
        io = pr.get("pers:interior_orientation", {})
        lignes.append({
            "id": fid, "collection": f.get("collection", ""), "pk_m": round(p, 1), "ecart_m": round(ecart, 1),
            "x_l93": round(px, 2), "y_l93": round(py, 2), "lon": lon, "lat": lat, "azimut_deg": az, "sens": sens,
            # dépôt public : le pseudonyme d'un contributeur individuel n'est pas repris (seuls les producteurs institutionnels)
            "date": pr.get("datetime", "")[:10],
            "producteur": pr.get("geovisio:producer", "") if pr.get("geovisio:producer", "") in ("région sud",)
            else "contributeur individuel (pseudonyme non repris)",
            "licence": pr.get("license", ""), "url_hd": f["assets"].get("hd", {}).get("href", ""),
            "url_sd": f["assets"].get("sd", {}).get("href", ""), "camera": io.get("camera_model", ""),
            "fov_deg": io.get("field_of_view", ""),
        })
    lignes.sort(key=lambda r: (r["collection"], r["pk_m"]))
    with open(LISTE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS); w.writeheader(); w.writerows(lignes)
    from collections import Counter
    c = Counter((r["date"][:7], r["producteur"], r["sens"], r["licence"], r["fov_deg"]) for r in lignes)
    print(f"{len(lignes)} images à moins de 25 m de l'axe -> {LISTE}")
    for k, v in sorted(c.items()):
        print("  ", k, v)


def vue_plane(equi: np.ndarray, cap_image: float, cap_vue: float, fov=90.0, largeur=1200, hauteur=None,
              tangage=0.0):
    """Vue perspective tirée d'une image équirectangulaire dont le centre regarde `cap_image` (°)."""
    H, W = equi.shape[:2]
    hauteur = hauteur or int(largeur * 0.62)
    f = (largeur / 2) / math.tan(math.radians(fov) / 2)
    u = np.arange(largeur) - largeur / 2 + 0.5
    v = np.arange(hauteur) - hauteur / 2 + 0.5
    uu, vv = np.meshgrid(u, v)
    lon = np.arctan2(uu, f)
    lat = -np.arctan2(vv * np.cos(lon), f) + math.radians(tangage)
    lon = lon + math.radians((cap_vue - cap_image + 540) % 360 - 180)
    px = ((lon / (2 * math.pi)) + 0.5) * W
    py = (0.5 - lat / math.pi) * H
    px = np.mod(px, W).astype(np.int32); py = np.clip(py, 0, H - 1).astype(np.int32)
    return equi[py, px]


def charger_liste():
    with open(LISTE, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def telecharger(pas=20.0, pk_min=-150, pk_max=3770, vues=True):
    from PIL import Image
    DOSSIER.mkdir(parents=True, exist_ok=True)
    (DOSSIER / "vues").mkdir(exist_ok=True)
    pk, x, y = axe()
    retenues = []
    lst = [r for r in charger_liste() if r["sens"] in ("montant", "descendant") and str(r["fov_deg"]) == "360"]
    for sens in ("descendant", "montant")[:1] if any(r["sens"] == "descendant" for r in lst) else ("montant",):
        # une seule collection par sens : la plus récente qui couvre le plus de linéaire
        par_col = {}
        for r in lst:
            if r["sens"] == sens:
                par_col.setdefault(r["collection"], []).append(r)
        if not par_col:
            continue
        cols = sorted(par_col.values(), key=lambda v: (-len(v), v[0]["date"]), reverse=False)
        prochain = pk_min
        for r in sorted([r for v in cols for r in v], key=lambda r: float(r["pk_m"])):
            p = float(r["pk_m"])
            if p < prochain or p > pk_max:
                continue
            retenues.append(r); prochain = p + pas
    print(f"{len(retenues)} images à télécharger (pas {pas} m)")
    for n, r in enumerate(retenues):
        dst = DOSSIER / f"{r['id']}.jpg"
        if not dst.exists():
            for essai in range(4):
                try:
                    rr = _session.get(r["url_hd"], timeout=120); rr.raise_for_status()
                    dst.write_bytes(rr.content); break
                except Exception as e:  # coupure réseau : on réessaie
                    print("  reprise", r["id"], e, flush=True)
                    import time; time.sleep(3 * (essai + 1))
        if vues:
            faire_vues(r, pk, x, y)
        if n % 20 == 0:
            print(f"  {n}/{len(retenues)}", flush=True)
    (DOSSIER / "retenues.json").write_text(json.dumps([r["id"] for r in retenues]), encoding="utf-8")


def faire_vues(r, pk=None, x=None, y=None, largeur=1400):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    if pk is None:
        pk, x, y = axe()
    src = DOSSIER / f"{r['id']}.jpg"
    sortie = DOSSIER / "vues" / f"{r['id']}_avant.jpg"
    if sortie.exists():
        return
    equi = np.asarray(Image.open(src).convert("RGB"))
    _, _, cap_route = projeter(pk, x, y, float(r["x_l93"]), float(r["y_l93"]))
    # image 360° : vues dans le sens de la montée, quel que soit le sens de prise ; sinon sens de prise
    if str(r.get("fov_deg")) == "360" or r["sens"] == "montant":
        cap_marche = cap_route
    else:
        cap_marche = (cap_route + 180) % 360
    az = float(r["azimut_deg"])
    for nom, dc, fov in (("avant", 0, 80), ("gauche", -75, 80), ("droite", 75, 80)):
        im = vue_plane(equi, az, cap_marche + dc, fov=fov, largeur=largeur)
        Image.fromarray(im).save(DOSSIER / "vues" / f"{r['id']}_{nom}.jpg", quality=86)


if __name__ == "__main__":
    a = sys.argv[1:] or ["inventaire"]
    if a[0] == "inventaire":
        inventaire()
    elif a[0] == "telecharger":
        pas = float(a[a.index("--pas") + 1]) if "--pas" in a else 20.0
        telecharger(pas)
    elif a[0] == "vue":
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        r = {x["id"]: x for x in charger_liste()}[a[1]]
        equi = np.asarray(Image.open(DOSSIER / f"{a[1]}.jpg").convert("RGB"))
        fov = float(a[3]) if len(a) > 3 else 60
        lg = int(a[4]) if len(a) > 4 else 1400
        im = vue_plane(equi, float(r["azimut_deg"]), float(a[2]), fov=fov, largeur=lg)
        out = DOSSIER / "vues" / f"{a[1]}_cap{int(float(a[2]))}_fov{int(fov)}.jpg"
        Image.fromarray(im).save(out, quality=90); print(out)


def planches(par_planche=8, champ=200.0, haut=20.0, bas=-32.0, largeur=800):
    """Planches de relevé : pour chaque image retenue, une bande équirectangulaire de `champ` degrés centrée sur le
    sens de la montée (gauche de la route à gauche), de `haut` à `bas` degrés d'élévation. Numérotées par PK."""
    from PIL import Image, ImageDraw
    Image.MAX_IMAGE_PIXELS = None
    pk, x, y = axe()
    L = {r["id"]: r for r in charger_liste()}
    fr = DOSSIER / "retenues.json"
    ids = json.loads(fr.read_text()) if fr.exists() else [p.stem for p in DOSSIER.glob("*.jpg")]
    ids = [i for i in ids if i in L and (DOSSIER / f"{i}.jpg").exists()]
    ids.sort(key=lambda i: float(L[i]["pk_m"]))
    dpl = DOSSIER / "planches"; dpl.mkdir(exist_ok=True)
    index = []
    bandes = []
    for i in ids:
        r = L[i]
        cache = dpl / f"bande_{i}.jpg"
        if not cache.exists():
            eq = Image.open(DOSSIER / f"{i}.jpg"); W, H = eq.size
            _, _, cap = projeter(pk, x, y, float(r["x_l93"]), float(r["y_l93"]))
            # colonne du cap `cap` : le centre de l'image (W/2) regarde azimut_deg
            c = (W / 2 + (cap - float(r["azimut_deg"])) / 360 * W) % W
            x0 = int(c - champ / 360 * W / 2); x1 = int(c + champ / 360 * W / 2)
            y0 = int((0.5 - haut / 180) * H); y1 = int((0.5 - bas / 180) * H)
            if x0 < 0 or x1 > W:
                eq = Image.fromarray(np.roll(np.asarray(eq), -x0, axis=1)); x1 -= x0; x0 = 0
            b = eq.crop((x0, y0, x1, y1)).resize((largeur, int(largeur * (y1 - y0) / (x1 - x0))), Image.LANCZOS)
            b.save(cache, quality=85)
        bandes.append((i, Image.open(cache)))
    for k in range(0, len(bandes), par_planche):
        lot = bandes[k:k + par_planche]
        h = lot[0][1].size[1] + 16
        pl = Image.new("RGB", (2 * largeur + 6, ((len(lot) + 1) // 2) * h), (0, 0, 0))
        d = ImageDraw.Draw(pl)
        for q, (i, b) in enumerate(lot):
            ox, oy = (q % 2) * (largeur + 6), (q // 2) * h
            pl.paste(b, (ox, oy + 16))
            n = k + q
            d.text((ox + 4, oy + 2), f"[{n}] PK {float(L[i]['pk_m']):.0f}   G <-  (montée au centre)  -> D   "
                                     f"id {i[:8]}", fill=(255, 255, 0))
            index.append({"n": n, "pk_m": float(L[i]["pk_m"]), "id": i, "planche": k // par_planche + 1})
        pl.save(dpl / f"planche_{k // par_planche + 1:02d}.jpg", quality=85)
    (dpl / "index.json").write_text(json.dumps(index, indent=0), encoding="utf-8")
    print(len(index), "bandes,", (len(index) + par_planche - 1) // par_planche, "planches")


if __name__ == "__main__" and sys.argv[1:2] == ["planches"]:
    planches()
