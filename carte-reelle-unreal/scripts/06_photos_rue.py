"""Étape 6 - Photos de rue Panoramax de la zone (référence visuelle des façades, sols, mobilier).

Interroge l'API STAC de Panoramax (https://api.panoramax.xyz/api/search) sur la bbox de la zone
de détail. L'API ne pagine pas une recherche : quand une requête renvoie le maximum demandé, la
bbox est coupée en quatre et chaque quart est réinterrogé. Les images sont ensuite filtrées à la
zone de détail exacte (utile pour un couloir).
Sur option (--vignettes ou photos_rue.vignettes dans zone.json), télécharge les vignettes (500 px
de large) des images les plus proches du centre, au plus photos_rue.max_vignettes.
Licence : propre à chaque image (colonne licence, souvent CC-BY-SA 4.0) : à citer si réutilisée.

Usage : python 06_photos_rue.py --zone zone.json --sortie DOSSIER [--vignettes] [--max N]
Sorties : photos/photos_rue.csv (id,lon,lat,x,y,cap,date,url_image,licence),
          photos/vignettes/<id>.jpg, journaux/06_photos_rue.json
"""
import csv
import json

import numpy as np
import shapely

import geo

LIMITE = 1000        # images par requête ; au-delà la bbox est subdivisée
PROF_MAX = 6         # profondeur de subdivision (bbox / 4^6) : garde-fou en zone très photographiée


def chercher(ctx, bbox, prof=0):
    params = {"bbox": ",".join(f"{v:.6f}" for v in bbox), "limit": LIMITE}
    b = geo.en_cache(ctx.cache, "panoramax", geo._cle(params), ".json",
                     lambda: geo.requete(geo.PANORAMAX, params, delai=90).content)
    feats = json.loads(b).get("features", [])
    if len(feats) < LIMITE or prof >= PROF_MAX:
        return feats, prof
    o, s, e, n = bbox
    mx, my = (o + e) / 2, (s + n) / 2
    out, pmax = [], prof
    for q in ((o, s, mx, my), (mx, s, e, my), (o, my, mx, n), (mx, my, e, n)):
        f, p = chercher(ctx, q, prof + 1)
        out += f
        pmax = max(pmax, p)
    return out, pmax


def ligne(ctx, f):
    p = f.get("properties", {})
    lon, lat = f["geometry"]["coordinates"][:2]
    a = f.get("assets", {})
    url = (a.get("sd") or a.get("hd") or {}).get("href") or p.get("geovisio:image", "")
    vign = (a.get("thumb") or {}).get("href") or p.get("geovisio:thumbnail", "")
    lic = p.get("license") or next((l.get("title", "") for l in f.get("links", []) if l.get("rel") == "license"), "")
    return {"id": f["id"], "lon": lon, "lat": lat, "cap": p.get("view:azimuth", ""), "date": (p.get("datetime") or "")[:10],
            "url_image": url, "licence": lic, "_vignette": vign}


def main():
    ap = geo.parser(__doc__.splitlines()[0])
    ap.add_argument("--vignettes", action="store_true", help="télécharge les vignettes")
    ap.add_argument("--max", type=int, help="nombre maximal de vignettes")
    args = ap.parse_args()
    ctx = geo.Contexte(args)
    pc = ctx.cfg["photos_rue"]
    vign = args.vignettes or bool(pc.get("vignettes"))
    nmax = args.max or int(pc.get("max_vignettes", 100))
    d = ctx.dossier("photos")
    csv_p = d / "photos_rue.csv"
    j = ctx.deja_fait("06_photos_rue", [csv_p], vignettes=vign, max=nmax)
    if j:
        geo.resume([f"06_photos_rue : déjà fait ({j['resume']}) ; --force pour refaire"])
        return
    zone = ctx.emprise_locale()
    bbox = ctx.bbox_lonlat(*zone.bounds)
    try:
        feats, prof = chercher(ctx, bbox)
    except Exception as e:      # Panoramax n'est qu'une référence : l'étape ne bloque pas la chaîne
        ctx.journal("06_photos_rue", {"options": {"vignettes": vign, "max": nmax}, "resume": "Panoramax injoignable",
                                      "erreur": str(e)[:300]})
        with open(csv_p, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["id", "lon", "lat", "x", "y", "cap", "date", "url_image", "licence"])
        geo.resume([f"06_photos_rue : Panoramax injoignable ({str(e)[:100]}) ; CSV vide écrit, chaîne non bloquée"])
        return
    vus, rows = set(), []
    for f in feats:
        if f.get("id") in vus or not f.get("geometry"):
            continue
        vus.add(f["id"])
        rows.append(ligne(ctx, f))
    if rows:
        x, y = ctx.lonlat_vers_local(np.array([r["lon"] for r in rows]), np.array([r["lat"] for r in rows]))
        dedans = shapely.contains_xy(zone, x, y)
        for r, xi, yi in zip(rows, x, y):
            r["x"], r["y"] = round(float(xi), 2), round(float(yi), 2)
        rows = [r for r, k in zip(rows, dedans) if k]
    rows.sort(key=lambda r: (r["date"], r["id"]), reverse=True)
    cols = ["id", "lon", "lat", "x", "y", "cap", "date", "url_image", "licence"]
    with open(csv_p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    n_v, echecs = 0, 0
    if vign and rows:
        dv = ctx.dossier("photos/vignettes")
        for r in sorted(rows, key=lambda r: r["x"] ** 2 + r["y"] ** 2)[:nmax]:
            if not r["_vignette"]:
                continue
            p = dv / f"{r['id']}.jpg"
            try:
                if not p.exists():
                    p.write_bytes(geo.requete(r["_vignette"], delai=60,
                                              accepte=lambda q: q.headers.get("content-type", "").startswith("image/")).content)
                    geo.Compteur.octets += p.stat().st_size
                    geo.Compteur.requetes += 1
                n_v += 1
            except Exception:       # une vignette manquante n'est pas grave
                echecs += 1
    dates = sorted(r["date"] for r in rows if r["date"])
    lic = {}
    for r in rows:
        lic[r["licence"]] = lic.get(r["licence"], 0) + 1
    txt = f"{len(rows)} images dans la zone" + (f", de {dates[0][:4]} à {dates[-1][:4]}" if dates else "")
    ctx.journal("06_photos_rue", {"options": {"vignettes": vign, "max": nmax}, "resume": txt, "images": len(rows),
                                  "trouvees_bbox": len(vus), "subdivision": prof, "licences": lic,
                                  "vignettes": n_v, "vignettes_echecs": echecs})
    geo.resume([f"06_photos_rue : {txt} ; vignettes : {n_v}" + (f" ({echecs} échecs)" if echecs else ""),
                f"  licences : " + ", ".join(f"{k or '?'} {v}" for k, v in lic.items()),
                f"  téléchargé : {geo.volume_telecharge()} ; {ctx.duree()}"])


if __name__ == "__main__":
    main()
