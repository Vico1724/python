"""Étape 7 - Maillages GLB : paysage lointain basse résolution et terrain proche.

lointain.glb : relief sur un carré de 2 x rayon_m (4 km par défaut) au pas pas_m (25 m), drapé de
  l'orthophoto basse résolution (03). Source : RGE ALTI (France) ou le MNT fourni à 02 (--mnt). La
  mer (sans donnée) est à l'altitude 0. Sous le Landscape, les sommets sont abaissés de
  abaissement_m (2 m) pour que les deux surfaces ne se chevauchent pas ; le bord du carré du
  terrain garde la vraie altitude, donc pas de fente visible.
terrain_proche.glb : le même relief que la heightmap, en maillage texturé (pas de 1 à 16 fois celui
  de la heightmap pour rester sous ~260 000 sommets). Sert d'aperçu, de terrain de secours si le
  Landscape ne convient pas, et de témoin du repère à l'import (bornes connues).
Repère glTF : X = est, Y = haut, Z = sud, mètres, origine du repère local.

Usage : python 07_lointain.py --zone zone.json --sortie DOSSIER
Sorties : lointain/lointain.glb, lointain/terrain_proche.glb, repere.json (rubrique maillages),
          journaux/07_lointain.json
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image

import geo

Image.MAX_IMAGE_PIXELS = None
SOMMETS_MAX_COTE = 513      # terrain proche : au plus 513 x 513 sommets (≈ 263 000)


def uv(X, Y, b):
    x0, y0, x1, y1 = b
    return np.column_stack([(X.ravel() - x0) / (x1 - x0), (Y.ravel() - y0) / (y1 - y0)])


def relief_lointain(ctx, rayon, pas):
    bornes = ctx.bornes_proj(rayon, pas)
    if ctx.repere.get("mnt_fourni"):
        a = geo.reprojeter(Path(ctx.repere["mnt_fourni"]), bornes, pas, ctx.crs, resampling="average")
        src = "MNT fourni"
    elif ctx.en_france():
        a = geo.wms_mosaique(ctx.cache, geo.COUCHE_RGEALTI, bornes, pas, progres="RGE ALTI lointain")[0]
        src = "RGE ALTI IGN"
    else:
        raise SystemExit("ERREUR 07_lointain : hors France sans MNT fourni : relancer 02_relief.py --mnt fichier.tif "
                         "avec un MNT qui couvre aussi le lointain (Copernicus GLO-30 par exemple)")
    trou = ~np.isfinite(a)
    a = np.where(trou, 0.0, a)          # mer ou hors couverture : altitude 0
    return a.astype(np.float32), src, round(float(trou.mean() * 100), 1)


def main():
    ap = geo.parser(__doc__.splitlines()[0])
    args = ap.parse_args()
    ctx = geo.Contexte(args)
    if ctx.repere.get("z0_m") is None:
        raise SystemExit("ERREUR 07_lointain : lancer d'abord 02_relief.py (z0 et relief du terrain)")
    if not ctx.repere.get("ortho"):
        raise SystemExit("ERREUR 07_lointain : lancer d'abord 03_ortho.py (textures)")
    d = ctx.dossier("lointain")
    sorties = [d / "lointain.glb", d / "terrain_proche.glb"]
    j = ctx.deja_fait("07_lointain", sorties)
    if j and ctx.repere.get("maillages"):
        geo.resume([f"07_lointain : déjà fait ({j['resume']}) ; --force pour refaire"])
        return
    z0 = ctx.repere["z0_m"]
    t = ctx.carre()
    demi, res, n = t["demi_cote_m"], t["pas_m"], t["taille_px"]
    lo = ctx.cfg["lointain"]
    ol = ctx.repere["ortho"]["lointain"]
    rayon = ol["bornes_locales"][2]                  # même carré que l'ortho lointaine (03)
    pas = float(lo["pas_m"])
    rayon = math.floor(rayon / pas) * pas

    # --- lointain
    a, src, mer = relief_lointain(ctx, rayon, pas)
    xs = np.arange(-rayon, rayon + pas / 2, pas)
    X, Y = np.meshgrid(xs, xs[::-1])
    Z = a - z0
    sous = (np.abs(X) < demi - 1e-6) & (np.abs(Y) < demi - 1e-6)
    Z = np.where(sous, Z - float(lo["abaissement_m"]), Z)
    img = Image.open(ctx.sortie / ol["fichier"])
    m_loin = geo.grille_maillage(X, Y, Z, img, uv(X, Y, ol["bornes_locales"]))
    b_loin = geo.ecrire_glb(d / "lointain.glb", [("SM_Lointain", m_loin)])

    # --- terrain proche
    mnt, _ = geo.lire_tif(ctx.sortie / "relief" / "mnt.tif")
    k = max(1, math.ceil(n / SOMMETS_MAX_COTE))
    while (n - 1) % k:
        k += 1
    zp = mnt[::k, ::k] - z0
    xp = -demi + np.arange(zp.shape[1]) * res * k
    Xp, Yp = np.meshgrid(xp, -xp)
    ot = ctx.repere["ortho"]["terrain"]
    m_proche = geo.grille_maillage(Xp, Yp, zp, Image.open(ctx.sortie / ot["fichier"]), uv(Xp, Yp, ot["bornes_locales"]))
    b_proche = geo.ecrire_glb(d / "terrain_proche.glb", [("SM_TerrainProche", m_proche)])

    ctx.repere["maillages"] = {
        "lointain": {"fichier": "lointain/lointain.glb", "texture": ol["fichier"], "bornes_cm": b_loin,
                     "cote_m": 2 * rayon, "pas_m": pas, "sommets": int(X.size), "source": src, "mer_ou_vide_pct": mer},
        "terrain_proche": {"fichier": "lointain/terrain_proche.glb", "texture": ot["fichier"], "bornes_cm": b_proche,
                           "cote_m": 2 * demi, "pas_m": res * k, "sommets": int(Xp.size)}}
    ctx.ecrire_repere()
    txt = (f"lointain {2 * rayon / 1000:.1f} km au pas {pas:g} m ({geo.taille_fichier(d / 'lointain.glb')}, "
           f"{mer} % mer/vide), terrain proche au pas {res * k:g} m ({geo.taille_fichier(d / 'terrain_proche.glb')})")
    ctx.journal("07_lointain", {"options": {}, "resume": txt, **ctx.repere["maillages"],
                                "altitudes_lointain_m": [round(float(a.min()), 1), round(float(a.max()), 1)]})
    geo.resume([f"07_lointain : {txt}",
                f"  altitudes lointain {a.min():.0f} à {a.max():.0f} m ; source {src}",
                f"  téléchargé : {geo.volume_telecharge()} ; {ctx.duree()}"])


if __name__ == "__main__":
    main()
