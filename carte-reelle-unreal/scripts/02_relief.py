"""Étape 2 - Relief : MNT du terrain, heightmap 16 bits pour un Landscape Unreal, MNT/MNS LiDAR fins.

Sources (France) : MNT LiDAR HD (Géoplateforme, 0,5 m natif) là où il existe, complété par le
RGE ALTI (1 m) ; les trous restants (mer, bord de couverture) sont bouchés : altitude 0 pour la mer,
valeur voisine sinon. Hors France ou au choix : --mnt fichier.tif (tout système de coordonnées).
La heightmap couvre le carré du terrain calculé par 01_emprise.py (taille 505, 1009, 2017, 4033
ou 8129 px). Les échelles Unreal exactes sont écrites dans repere.json (rubrique unreal_landscape).
Pour la végétation (05) et la hauteur des bâtiments (08), MNT et MNS LiDAR à 0,5 m sont aussi
téléchargés sur la zone de détail quand le LiDAR HD couvre la zone.

Usage : python 02_relief.py --zone zone.json --sortie DOSSIER [--mnt fichier.tif] [--sans-lidar-fin]
Sorties : relief/mnt.tif (altitudes, pas du terrain), relief/heightmap_<N>.png et .r16,
          relief/mnt_50cm.tif + relief/mns_50cm.tif (si LiDAR HD), repere.json complété,
          journaux/02_relief.json
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image

import geo

MER_M = 3.0          # un trou bordé de terrain plus bas que 3 m est de la mer : altitude 0
FIN_RES = 0.5        # pas natif du LiDAR HD
FIN_MAX_PX = 64e6    # au-delà (≈ 16 km² à 0,5 m), les rasters fins passent à 1 m pour rester sous 256 Mo


def mnt_terrain(ctx, args, bornes, res):
    """Renvoie (altitudes, info sources)."""
    fichier = args.mnt or ctx.cfg["sources"].get("mnt")
    if fichier:
        p = Path(fichier).resolve()
        a = geo.reprojeter(p, bornes, res, ctx.crs)
        return a, {"source": f"fichier fourni ({p.name})", "couverture_pct": round(float(np.isfinite(a).mean() * 100), 1)}
    if not ctx.en_france():
        raise SystemExit("ERREUR 02_relief : zone hors France, pas de MNT IGN. Fournir un MNT avec --mnt fichier.tif "
                         "(par ex. Copernicus GLO-30, SRTM, ou un LiDAR national), ou \"sources\": {\"mnt\": ...} "
                         "dans zone.json.")
    lidar = geo.wms_mosaique(ctx.cache, geo.COUCHE_LIDAR_MNT, bornes, res, progres="MNT LiDAR HD")[0]
    alti = geo.wms_mosaique(ctx.cache, geo.COUCHE_RGEALTI, bornes, res, progres="RGE ALTI")[0]
    cl, ca = float(np.isfinite(lidar).mean()), float(np.isfinite(alti).mean())
    if cl == 0 and ca == 0:
        raise SystemExit("ERREUR 02_relief : ni LiDAR HD ni RGE ALTI sur cette zone (mer, ou hors couverture IGN). "
                         "Fournir un MNT avec --mnt fichier.tif.")
    a = np.where(np.isfinite(lidar), lidar, alti)
    ecart = lidar - alti
    ok = np.isfinite(ecart)
    return a, {"source": "LiDAR HD" if cl > 0.99 else "RGE ALTI" if cl == 0 else "LiDAR HD + RGE ALTI",
               "couverture_lidar_pct": round(cl * 100, 1), "couverture_rgealti_pct": round(ca * 100, 1),
               "ecart_lidar_rgealti_m": ({"median": round(float(np.median(ecart[ok])), 2),
                                          "p95_abs": round(float(np.percentile(np.abs(ecart[ok]), 95)), 2)}
                                         if ok.any() else None),
               "_lidar": cl}


def boucher_mer(a):
    """Trous : mer (0 m) s'ils sont bordés de terrain bas, sinon la valeur voisine."""
    trou = ~np.isfinite(a)
    if not trou.any():
        return a, 0, 0
    voisin, n = geo.boucher(a)
    mer = trou & (voisin < MER_M)
    out = np.where(mer, 0.0, voisin).astype(np.float32)
    return out, int(mer.sum()), int((trou & ~mer).sum())


def lidar_fin(ctx, args):
    """MNT et MNS LiDAR à 0,5 m sur la zone de détail (grille alignée sur le demi-mètre)."""
    x0, y0, x1, y1 = ctx.repere["bornes_detail_locales"]
    res = FIN_RES
    if (x1 - x0) * (y1 - y0) / res ** 2 > FIN_MAX_PX:
        res = 1.0
    b = (math.floor(x0 + ctx.ox), math.floor(y0 + ctx.oy), math.ceil(x1 + ctx.ox), math.ceil(y1 + ctx.oy))
    d = ctx.dossier("relief")
    out = {}
    for nom, couche in (("mnt", geo.COUCHE_LIDAR_MNT), ("mns", geo.COUCHE_LIDAR_MNS)):
        a = geo.wms_mosaique(ctx.cache, couche, b, res, progres=f"{nom.upper()} LiDAR fin")[0]
        geo.ecrire_tif(d / f"{nom}_50cm.tif", np.nan_to_num(a, nan=geo.NODATA), b, res, ctx.crs, nodata=geo.NODATA)
        out[nom] = round(float(np.isfinite(a).mean() * 100), 1)
    return {"pas_m": res, "bornes_proj": b, "couverture_pct": out}


def main():
    ap = geo.parser(__doc__.splitlines()[0])
    ap.add_argument("--mnt", help="MNT fourni (GeoTIFF, tout système) à la place des sources IGN")
    ap.add_argument("--sans-lidar-fin", action="store_true", help="ne télécharge pas MNT/MNS à 0,5 m (pas d'arbres LiDAR)")
    args = ap.parse_args()
    ctx = geo.Contexte(args)
    t = ctx.carre()
    n, res, demi = t["taille_px"], t["pas_m"], t["demi_cote_m"]
    d = ctx.dossier("relief")
    hm = d / f"heightmap_{n}.png"
    opts = {"mnt": args.mnt, "sans_lidar_fin": args.sans_lidar_fin}
    j = ctx.deja_fait("02_relief", [d / "mnt.tif", hm], **opts)
    if j and ctx.repere.get("unreal_landscape"):
        geo.resume([f"02_relief : déjà fait ({j['resume']}) ; --force pour refaire"])
        return

    bornes = ctx.bornes_proj(demi, res)                     # bord des pixels = sommets ± demi-pas
    a, info = mnt_terrain(ctx, args, bornes, res)
    a, n_mer, n_bouche = boucher_mer(a)
    if a.shape != (n, n):
        raise SystemExit(f"ERREUR 02_relief : grille {a.shape} au lieu de {n} x {n}")
    geo.ecrire_tif(d / "mnt.tif", a, bornes, res, ctx.crs, nodata=geo.NODATA)

    z0 = round(float(a[n // 2, n // 2]), 1)                 # sol à l'origine : z = 0 du repère local
    z = a - z0
    zmin, zmax = float(z.min()), float(z.max())
    plage = max(zmax - zmin, 1.0)                           # terrain plat : plage minimale de 1 m
    v = np.round((z - zmin) / plage * 65535).astype(np.uint16)
    Image.fromarray(v).save(hm)
    v.astype("<u2").tofile(d / f"heightmap_{n}.r16")
    relu = np.asarray(Image.open(hm))
    if not np.array_equal(relu.astype(np.int64), v.astype(np.int64)):
        raise SystemExit("ERREUR 02_relief : la heightmap relue diffère de celle écrite")

    # Unreal : hauteur (cm) = position Z + (valeur - 32768) * échelle Z / 128 ; on veut zmin pour 0, zmax pour 65535.
    ech_z = plage * 100 * 128 / 65535
    pos_z = zmin * 100 + 32768 / 65535 * plage * 100
    ue = {"fichier": hm.name, "taille_px": n, "echelle_cm": {"x": res * 100, "y": res * 100, "z": round(ech_z, 6)},
          "position_centre_cm": [0.0, 0.0, round(pos_z, 2)],
          "position_coin_acteur_cm": [-demi * 100, -demi * 100, round(pos_z, 2)],
          "formule": "z_local_m = z_min_m + valeur / 65535 * (z_max_m - z_min_m) ; altitude = z_local + z0",
          "consigne": "Mode Landscape > Manage > New > Import from File : choisir le PNG, Location = "
                      "position_centre_cm (l'outil centre le Landscape sur ce point), Scale = echelle_cm. "
                      "La ligne 0 de l'image est au nord (UE -Y).",
          "z_min_m": round(zmin, 3), "z_max_m": round(zmin + plage, 3)}
    ctx.repere.update({"z0_m": z0, "altitude_min_m": round(float(a.min()), 2), "altitude_max_m": round(float(a.max()), 2),
                       "unreal_landscape": ue})
    fin = None
    if ctx.en_france() and not args.mnt and not args.sans_lidar_fin and info.get("couverture_lidar_pct", 0) > 0:
        fin = lidar_fin(ctx, args)
    info.pop("_lidar", None)
    ctx.repere["lidar_fin"] = fin
    ctx.repere["mnt_fourni"] = str(Path(args.mnt or ctx.cfg["sources"].get("mnt")).resolve()) if (args.mnt or ctx.cfg["sources"].get("mnt")) else None
    ctx.ecrire_repere()
    pente = np.degrees(np.arctan(np.hypot(*np.gradient(a, res))))
    txt = (f"{n} x {n} px au pas {res} m, altitudes {a.min():.1f} à {a.max():.1f} m, z0 {z0} m, "
           f"source {info['source']}")
    ctx.journal("02_relief", {"options": opts, "resume": txt, "sources": info, "pixels_mer": n_mer,
                              "pixels_bouches": n_bouche, "z0_m": z0, "unreal_landscape": ue, "lidar_fin": fin,
                              "pente_deg": {"mediane": round(float(np.median(pente)), 1),
                                            "p95": round(float(np.percentile(pente, 95)), 1)}})
    lignes = [f"02_relief : {txt}",
              f"  Unreal : échelle X/Y {res * 100:g} cm, Z {ech_z:.4f} ; position (centre) Z {pos_z:.1f} cm",
              f"  trous bouchés : {n_bouche} px, mer : {n_mer} px ; LiDAR fin : "
              + (f"MNT {fin['couverture_pct']['mnt']} %, MNS {fin['couverture_pct']['mns']} %" if fin else "non"),
              f"  téléchargé : {geo.volume_telecharge()} ; {ctx.duree()}"]
    geo.resume(lignes)


if __name__ == "__main__":
    main()
