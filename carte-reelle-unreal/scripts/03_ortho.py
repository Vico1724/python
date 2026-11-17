"""Étape 3 - Orthophoto : texture du terrain et version basse résolution pour le lointain.

Source (France) : BD ORTHO (Géoplateforme, couche HR.ORTHOIMAGERY.ORTHOPHOTOS, 20 cm natif),
téléchargée en dalles puis assemblée. Hors France ou au choix : --ortho fichier.tif (GeoTIFF RVB,
tout système de coordonnées).
La texture du terrain couvre exactement le Landscape (du premier au dernier sommet de la heightmap),
donc les UV 0-1 du Landscape tombent juste. Sa taille est plafonnée à texture_max_px (8192 par
défaut) : au-delà, le pas effectif grossit et il est noté dans repere.json.

Usage : python 03_ortho.py --zone zone.json --sortie DOSSIER [--ortho fichier.tif]
Sorties : ortho/ortho.tif (GeoTIFF), ortho/ortho_terrain.jpg, ortho/ortho_lointain.jpg,
          repere.json (rubrique ortho), journaux/03_ortho.json
"""
from pathlib import Path

import numpy as np
from PIL import Image

import geo

Image.MAX_IMAGE_PIXELS = None        # textures de 8192 px et plus : pas une attaque


def vide_pct(a):
    """Part de pixels sans image (blanc ou noir purs) : hors couverture de la source."""
    s = a.astype(np.int16).sum(axis=0)
    return round(float(((s == 0) | (s == 765)).mean() * 100), 2)


def obtenir(ctx, fichier, bornes, res, nom):
    if fichier:
        return geo.reprojeter(Path(fichier).resolve(), bornes, res, ctx.crs, bandes=3)
    return geo.wms_mosaique(ctx.cache, geo.COUCHE_ORTHO, bornes, res, fmt="image/jpeg", bandes=3, progres=nom)


def main():
    ap = geo.parser(__doc__.splitlines()[0])
    ap.add_argument("--ortho", help="orthophoto fournie (GeoTIFF RVB, tout système) à la place de la BD ORTHO")
    args = ap.parse_args()
    ctx = geo.Contexte(args)
    fichier = args.ortho or ctx.cfg["sources"].get("ortho")
    if not fichier and not ctx.en_france():
        raise SystemExit("ERREUR 03_ortho : zone hors France, pas de BD ORTHO. Fournir une orthophoto avec "
                         "--ortho fichier.tif (photo aérienne nationale, ou Sentinel-2 à 10 m si rien d'autre), "
                         "ou \"sources\": {\"ortho\": ...} dans zone.json.")
    d = ctx.dossier("ortho")
    sorties = [d / "ortho.tif", d / "ortho_terrain.jpg", d / "ortho_lointain.jpg"]
    j = ctx.deja_fait("03_ortho", sorties, ortho=fichier)
    if j and ctx.repere.get("ortho"):
        geo.resume([f"03_ortho : déjà fait ({j['resume']}) ; --force pour refaire"])
        return

    t = ctx.carre()
    demi = t["demi_cote_m"]
    res_voulu = float(ctx.cfg["resolution_ortho_m"])
    px = min(round(2 * demi / res_voulu), int(ctx.cfg["texture_max_px"]))
    res = 2 * demi / px
    bornes = ctx.bornes_proj(demi)
    a = obtenir(ctx, fichier, bornes, res, "ortho terrain")
    geo.ecrire_tif(d / "ortho.tif", a, bornes, res, ctx.crs, image=True)
    Image.fromarray(np.moveaxis(a, 0, -1)).save(d / "ortho_terrain.jpg", quality=90)

    lo = ctx.cfg["lointain"]
    rayon = max(float(lo["rayon_m"]), demi * 1.5)
    lpx = int(lo["texture_px"])
    lb = ctx.bornes_proj(rayon)
    b = obtenir(ctx, fichier, lb, 2 * rayon / lpx, "ortho lointain")
    Image.fromarray(np.moveaxis(b, 0, -1)).save(d / "ortho_lointain.jpg", quality=85)

    info = {"terrain": {"fichier": "ortho/ortho_terrain.jpg", "px": px, "pas_m": round(res, 4),
                        "bornes_locales": [-demi, -demi, demi, demi], "vide_pct": vide_pct(a)},
            "lointain": {"fichier": "ortho/ortho_lointain.jpg", "px": lpx, "pas_m": round(2 * rayon / lpx, 3),
                         "bornes_locales": [-rayon, -rayon, rayon, rayon], "vide_pct": vide_pct(b)},
            "source": f"fichier fourni ({Path(fichier).name})" if fichier else "BD ORTHO IGN (Licence Ouverte Etalab 2.0)",
            "convention_uv": "u = (x - x_min) / largeur, v = (y_max - y) / hauteur ; ligne 0 au nord"}
    ctx.repere["ortho"] = info
    ctx.ecrire_repere()
    txt = (f"terrain {px} x {px} px à {res:.2f} m ({info['terrain']['vide_pct']} % vide), lointain {lpx} px "
           f"sur {2 * rayon / 1000:.1f} km à {2 * rayon / lpx:.1f} m")
    ctx.journal("03_ortho", {"options": {"ortho": fichier}, "resume": txt, **info})
    lignes = [f"03_ortho : {txt}", f"  téléchargé : {geo.volume_telecharge()} ; {ctx.duree()}"]
    if res > res_voulu * 1.01:
        lignes.insert(1, f"  pas porté de {res_voulu} à {res:.2f} m (texture plafonnée à {ctx.cfg['texture_max_px']} px)")
    if info["terrain"]["vide_pct"] > 1:
        lignes.insert(1, "  ATTENTION : orthophoto incomplète sur le terrain")
    geo.resume(lignes)


if __name__ == "__main__":
    main()
