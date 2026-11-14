"""Sols « façon jeu », première moitié : dit, pour chaque demi-mètre du terrain, de quelles matières le sol est fait.

Pourquoi. Jusqu'ici notre terrain portait la photo aérienne de l'IGN : juste vue de loin, floue de près (20 cm par
point au mieux). Le jeu habille ses terrains autrement : six matières détaillées qui se répètent (paillis forestier,
aiguilles de pin, herbe haute, herbe sèche, terre, cailloux), mélangées d'après des « masques » peints, et teintées par
une carte de couleur vue du ciel. Ce script prépare le mélange ; scripts/16_paquet_unreal.py en tire les masques et la
carte dans le repère du jeu (--sol jeu), et le terrain prend pour parent le matériau de terrain de Bollène.

Sources, toutes déjà dans data/raw (IGN) : hauteur de la végétation (MNS - MNT du LiDAR HD, 50 cm), photo infrarouge
(vigueur de la végétation, NDVI), photo couleur (clarté du sol nu), emprise de la chaussée (chaussee_precise.csv).

Règles (proportions, dont la somme fait 1 avec le paillis, qui est la matière de fond du jeu) :
  sous les arbres (plus de 2 à 5 m de haut)   aiguilles de pin et paillis, mêlés par un bruit doux ;
  garrigue (0,4 à 2 m)                         herbe sèche, cailloux, un peu d'aiguilles et de paillis ;
  sol ouvert et vert                           herbe sèche, herbe haute là où la végétation est très vigoureuse ;
  sol ouvert et nu                             cailloux s'il est clair (calcaire), terre s'il est sombre ;
  à moins de 1,5 m de la chaussée              cailloux (accotement) ; sous la chaussée : cailloux.
Ce sont des règles de bon sens, pas un relevé de terrain : elles donnent la bonne matière au bon endroit dans les
grandes lignes (forêt, garrigue, clairière, accotement), pas au mètre près.

Sorties (modele/sols_jeu/) : proportions_l93.npz (cinq couches, 0 à 255, 50 cm), couleur_1m.npy (photo moyennée à 1 m
pour la carte de couleur), sols_jeu.json (emprise, parts de chaque matière), apercu_matieres.jpg.
Usage : python scripts/15b_sols_du_jeu.py
"""
import csv
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.features import rasterize
from scipy import ndimage as ndi
from shapely.geometry import Polygon
from shapely.ops import unary_union

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
RAW, OUT = RACINE / "data" / "raw", RACINE / "modele" / "sols_jeu"
COUCHES = ["aiguilles_de_pin", "herbe_haute", "herbe_seche", "terre", "cailloux"]      # matières 2 à 6 du jeu
COULEURS_APERCU = {"paillis": (176, 160, 132), "aiguilles_de_pin": (150, 105, 60), "herbe_haute": (70, 140, 50),
                   "herbe_seche": (190, 175, 95), "terre": (120, 90, 70), "cailloux": (205, 200, 190)}
ACCOTEMENT_M = 1.5                # (ancien réglage : largeur de l'accotement de cailloux, gardé pour le bilan)
# Relevé du quatrième essai (13/11/2026) : sur une vingtaine de paires, l'accotement d'herbe verte rase de la route
# réelle (1 à 3 m, souvent jusqu'au ras de l'enrobé) était rendu en gravier gris ou en terre. Le liseré de pierraille
# est donc réduit à un filet, et l'herbe verte prend presque toute la bande.
ACCOTEMENT_LISERE_DE_M = 0.02     # le liseré de pierraille est plein jusqu'à 2 cm du bord de l'enrobé...
ACCOTEMENT_LISERE_M = 0.40        # ... et s'efface à 40 cm
ACCOTEMENT_HERBE_M = (2.2, 3.6)   # la bande d'herbe verte est pleine jusqu'à 2,2 m du bord et s'efface à 3,6 m
PENTE_ROCHE = (30.0, 48.0)       # degrés : en dessous, pas de roche ; au-dessus, roche à 85 %
NDVI_NU, NDVI_VERT = 0.03, 0.15
NDVI_VIGOUREUX = (0.30, 0.42)
CLARTE_CALCAIRE = (90.0, 130.0)
GRAINE = 20261112


def marche(x, a, b):
    """0 sous a, 1 au-dessus de b, raccord doux entre les deux."""
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def bruit(forme, maille_px, rng):
    """Champ aléatoire doux entre 0 et 1, de longueur d'onde `maille_px` points."""
    h, w = forme
    petit = rng.random((h // maille_px + 3, w // maille_px + 3)).astype(np.float32)
    grand = ndi.zoom(petit, maille_px, order=3)[:h, :w]
    lo, hi = np.percentile(grand[::7, ::7], [2, 98])
    return np.clip((grand - lo) / (hi - lo), 0.0, 1.0)


def lire(nom, forme, bandes=None):
    with rasterio.open(RAW / nom) as d:
        a = d.read(bandes, out_shape=((len(bandes) if bandes else d.count),) + forme, resampling=Resampling.average)
        return a.astype(np.float32), d.bounds


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(GRAINE)
    with rasterio.open(RAW / "mnt_lidarhd_50cm.tif") as d:
        mnt = d.read(1).astype(np.float32)
        tr, bornes, forme = d.transform, d.bounds, d.shape
    with rasterio.open(RAW / "mns_lidarhd_50cm.tif") as d:
        mnh = np.clip(d.read(1).astype(np.float32) - mnt, 0.0, 40.0)
    # pente du terrain : les talus taillés dans le rocher (une quarantaine de tronçons relevés sur la vidéo de
    # reconnaissances, surtout à gauche) sont des pentes raides ; elles reçoivent la matière « cailloux »
    gy, gx = np.gradient(np.where(np.isfinite(mnt), mnt, 0.0), tr.a)
    raide = ndi.gaussian_filter(marche(np.degrees(np.arctan(np.hypot(gx, gy))), PENTE_ROCHE[0], PENTE_ROCHE[1]), 1.0)
    del mnt, gx, gy
    mnh[~np.isfinite(mnh)] = 0.0
    irc, _ = lire("ortho_irc_20cm.tif", forme, [1, 2])                      # proche infrarouge, rouge
    ndvi = (irc[0] - irc[1]) / np.maximum(irc[0] + irc[1], 1.0)
    rvb, _ = lire("ortho_20cm.tif", forme)
    clarte = 0.299 * rvb[0] + 0.587 * rvb[1] + 0.114 * rvb[2]
    # les photos ne couvrent que le couloir de la spéciale : ailleurs elles sont noires, et rien n'y est classé
    valide = ndi.binary_erosion((irc.sum(0) > 6.0) & (rvb.sum(0) > 9.0), iterations=2)
    del irc, rvb

    # couvert : arbres, garrigue, sol ouvert
    arbres = ndi.gaussian_filter(marche(mnh, 2.0, 5.0), 1.5)
    garrigue = ndi.gaussian_filter(marche(mnh, 0.4, 1.2), 1.0) * (1.0 - arbres)
    ouvert = np.clip(1.0 - arbres - garrigue, 0.0, 1.0)
    del mnh
    # seuils réglés sur ces photos-ci (8 bits, non étalonnées) : le sol nu y a un NDVI sous 0,05, les arbres autour
    # de 0,2 à 0,4 ; le calcaire nu a une clarté médiane de 128 sur 255
    vert = marche(ndi.gaussian_filter(ndvi, 1.0), NDVI_NU, NDVI_VERT)
    vigoureux = marche(ndvi, *NDVI_VIGOUREUX)
    clair = marche(ndi.gaussian_filter(clarte, 1.0), *CLARTE_CALCAIRE)
    del ndvi, clarte
    b1, b2 = bruit(forme, 12, rng), bruit(forme, 50, rng)                    # 6 m et 25 m
    melange = 0.6 * b1 + 0.4 * b2

    # Depuis le 13/11/2026 (data/reference/matieres_du_jeu.json) les six matières ne sont plus celles de Bollène :
    # le fond (« paillis ») est un sol pierreux clair, « herbe_haute » une herbe rase verte, « cailloux » de la roche
    # calcaire. Vu en jeu : sol anthracite et nu, herbe absente, alors que la réalité montre de la pierraille claire,
    # de la litière rousse et de l'herbe verte. Le calcaire nu passe donc surtout au fond pierreux, la roche est
    # gardée pour les affleurements et les pentes raides, et l'herbe verte est plus présente.
    p = {}
    # Relevé du sixième essai (13/11/2026 au soir) : « sol brun nu sous les pins », alors que la reconnaissance montre de
    # l'herbe, de la garrigue et de la pierraille claire entre les troncs. La litière d'aiguilles couvre donc moins, et
    # l'herbe se glisse sous les arbres ; le reste revient au fond pierreux clair.
    p["aiguilles_de_pin"] = arbres * (0.34 + 0.30 * melange) + garrigue * 0.15
    p["herbe_haute"] = ouvert * vert * (0.25 + 0.60 * vigoureux) + arbres * 0.10 * (1.0 - melange)
    p["herbe_seche"] = ouvert * vert * (0.75 - 0.60 * vigoureux) * (0.65 + 0.35 * b1) + garrigue * (0.30 + 0.15 * b2) + arbres * 0.14 * b1
    p["terre"] = ouvert * (1.0 - vert) * (1.0 - clair)
    p["cailloux"] = 0.35 * ouvert * (1.0 - vert) * clair + garrigue * 0.10 * (1.0 - b1)
    del arbres, garrigue, ouvert, vert, vigoureux, clair, b2, melange

    # Pentes raides : roche pour moitié seulement, terre et herbe sèche pour le reste. Relevé du quatrième essai
    # (13/11/2026) : des talus de terre étaient rendus en surfaces grises lisses « d'aspect rocheux », à la texture
    # étirée (la matière du sol est plaquée d'en haut : sur une pente, la roche s'étire).
    for k in COUCHES:
        p[k] *= (1.0 - 0.70 * raide)
    p["cailloux"] += 0.45 * raide
    p["terre"] += 0.25 * raide
    part_raide = float(raide.mean())

    # chaussée et accotement
    with open(RACINE / "data" / "processed" / "chaussee_precise.csv", encoding="utf-8") as f:
        r = list(csv.DictReader(f))
    g = np.array([[float(x["x_gauche"]), float(x["y_gauche"])] for x in r])
    d_ = np.array([[float(x["x_droite"]), float(x["y_droite"])] for x in r])
    quads = [Polygon([g[i], g[i + 1], d_[i + 1], d_[i]]).buffer(0) for i in range(len(g) - 1)]
    ruban = unary_union([q for q in quads if q.is_valid and not q.is_empty])
    sur_route = rasterize([(ruban, 1)], out_shape=forme, transform=tr, fill=0, all_touched=True, dtype="uint8").astype(bool)
    dist = ndi.distance_transform_edt(~sur_route) * tr.a                     # mètres jusqu'à la chaussée
    # Distance EXACTE au bord de la chaussée pour les pixels proches. Vu en jeu le 13/11/2026 (troisième version) : les
    # bords de l'asphalte « zigzaguent ». La distance ci-dessus part de la chaussée dessinée sur la grille de 50 cm ; le
    # liseré de pierraille, large d'un demi-pixel, suivait donc la grille en marches d'escalier au lieu de suivre le bord.
    import shapely
    from scipy.spatial import cKDTree
    ys, xs = np.nonzero(dist < 6.0)
    X, Y = tr * (xs + 0.5, ys + 0.5)
    bords = []
    for b in (g, d_):
        n = np.maximum(np.ceil(np.linalg.norm(np.diff(b, axis=0), axis=1) / 0.04).astype(int), 1)
        bords.append(np.vstack([b[i] + (b[i + 1] - b[i]) * (np.arange(n[i]) / n[i])[:, None] for i in range(len(b) - 1)]))
    d_bord = cKDTree(np.vstack(bords)).query(np.column_stack([X, Y]))[0]
    shapely.prepare(ruban)
    dedans = shapely.contains_xy(ruban, X, Y)
    dist[ys, xs] = np.where(dedans, 0.0, d_bord)
    sur_route[ys, xs] = dedans
    # Accotement (vidéo de reconnaissances) : un liseré de pierraille de 30 à 50 cm au ras de l'enrobé, puis une
    # bande d'herbe rase verte jusqu'à 2 ou 3 m, irrégulière, qui laisse la place à la roche sur les talus raides.
    lisere = np.where(sur_route, 1.0, 1.0 - marche(dist, ACCOTEMENT_LISERE_DE_M, ACCOTEMENT_LISERE_M)).astype(np.float32)
    herbe = (marche(dist, ACCOTEMENT_LISERE_DE_M, ACCOTEMENT_LISERE_M) * (1.0 - marche(dist, ACCOTEMENT_HERBE_M[0], ACCOTEMENT_HERBE_M[1]))
             * (0.85 + 0.15 * b1) * (1.0 - raide)).astype(np.float32)
    herbe[sur_route] = 0.0
    accot = np.maximum(lisere, herbe)
    del dist, b1, raide
    for k in COUCHES:
        p[k] *= (1.0 - accot)                   # sous la chaussée et dans le liseré : le fond pierreux seul
    p["herbe_haute"] += herbe * 0.95

    # aires de terre et débouchés de pistes (data/reference/aires_et_pistes.json) : terre claire, ou le fond pierreux seul
    import regles_arbres
    emprises = regles_arbres.emprises_degagees(RACINE)
    for matiere in ("terre", "pierre", "sentier"):          # « sentier » : sentier étroit de l'IGN, en terre battue
        polys = [(g_, 1) for g_, m_ in emprises if m_ == matiere]
        if not polys:
            continue
        aire = ndi.gaussian_filter(rasterize(polys, out_shape=forme, transform=tr, fill=0, all_touched=True, dtype="uint8").astype(np.float32),
                                   0.7 if matiere == "sentier" else 1.2)
        aire[sur_route] = 0.0
        for k in COUCHES:
            p[k] *= (1.0 - aire)
        if matiere != "pierre":
            p["terre"] += (0.65 if matiere == "sentier" else 0.8) * aire
        del aire

    # Talus de rocaille (parois_rocheuses.json, genre « eboulis », relus le 13/11/2026) : pierres, roche brisée et terre
    # claire. Le sol y est peint en pierraille mêlée de terre ; 16_paquet_unreal.py y sème des pierres calcaires.
    roc = regles_arbres.rocailles(RACINE)
    if roc:
        m_roc = ndi.gaussian_filter(rasterize([(g_, 1) for g_, _ in roc], out_shape=forme, transform=tr, fill=0, all_touched=True,
                                              dtype="uint8").astype(np.float32), 1.0)
        m_roc[sur_route] = 0.0
        for k in COUCHES:
            p[k] *= (1.0 - 0.8 * m_roc)
        # sixième essai : « sol gris » sous de gros blocs, là où la reconnaissance montre de la terre ocre et du cailloutis
        p["cailloux"] += 0.34 * m_roc
        p["terre"] += 0.30 * m_roc
        del m_roc

    # hors des photos : le mélange de sous-bois, faute de mieux (peu de terrain s'y trouve)
    for k in COUCHES:
        p[k] = np.where(valide, p[k], (herbe * 0.85 if k == "herbe_haute" else 0.0)
                        + (1.0 - accot) * (0.45 if k == "aiguilles_de_pin" else 0.0)).astype(np.float32)
    total = sum(p.values())
    trop = np.maximum(total, 1.0)
    for k in COUCHES:
        p[k] = np.clip(p[k] / trop, 0.0, 1.0)
    paillis = np.clip(1.0 - sum(p.values()), 0.0, 1.0)
    parts = {"paillis": float(paillis[valide].mean()), **{k: float(p[k][valide].mean()) for k in COUCHES}}

    np.savez_compressed(OUT / "proportions_l93.npz", **{k: np.round(p[k] * 255).astype(np.uint8) for k in COUCHES})
    # photo couleur moyennée à 1 m, pour la carte de couleur
    forme1 = (forme[0] // 2, forme[1] // 2)
    rvb1, _ = lire("ortho_20cm.tif", forme1)
    noir = rvb1.sum(0) <= 9.0                 # hors photo : la couleur des environs, très adoucie, puis la moyenne
    if noir.any():
        poids = (~noir).astype(np.float32)
        voisin = ndi.gaussian_filter(poids, 40.0)
        moyenne = rvb1[:, ~noir].mean(1)
        part = np.clip(voisin / 0.05, 0.0, 1.0)
        for k in range(3):
            flou = ndi.gaussian_filter(rvb1[k] * poids, 40.0) / np.maximum(voisin, 1e-3)
            rvb1[k] = np.where(noir, flou * part + moyenne[k] * (1.0 - part), rvb1[k])
    # Là où l'étape 14 a produit une dalle de sol, sa couleur remplace la photo : sous les arbres, la photo montre les
    # houppiers, sombres, alors que la dalle porte un sol reconstruit (aiguilles, litière, cailloux). Vu en jeu le
    # 12/11/2026 : teinté par les houppiers, le sol sous les arbres était anthracite au lieu d'une terre claire.
    sol14 = np.zeros(forme1, bool)
    f14 = RACINE / "data" / "processed" / "textures_sol.json"
    if f14.exists():
        pas1 = tr.a * 2
        for d in json.loads(f14.read_text(encoding="utf-8"))["dalles"]:
            src14 = RACINE / "modele" / d["couleur"]
            if not src14.exists():
                continue
            em, cz = d["emprise_l93"], d["dalle_l93"]
            n14 = int(round((em[2] - em[0]) / pas1))
            im = np.asarray(Image.open(src14).convert("RGB").resize((n14, n14), Image.BOX), np.float32)
            c0, r0 = int(round((cz[0] - em[0]) / pas1)), int(round((em[3] - cz[3]) / pas1))
            nc, nr = int(round((cz[2] - cz[0]) / pas1)), int(round((cz[3] - cz[1]) / pas1))
            col, lig = int(round((cz[0] - bornes.left) / pas1)), int(round((bornes.top - cz[3]) / pas1))
            if col < 0 or lig < 0 or col + nc > forme1[1] or lig + nr > forme1[0]:
                continue
            rvb1[:, lig:lig + nr, col:col + nc] = im[r0:r0 + nr, c0:c0 + nc].transpose(2, 0, 1)
            sol14[lig:lig + nr, col:col + nc] = True
    np.save(OUT / "couleur_1m.npy", np.clip(rvb1, 0, 255).astype(np.uint8).transpose(1, 2, 0))
    np.save(OUT / "couleur_1m_sol14.npy", sol14)
    moyenne_valide = [round(float(v), 1) for v in rvb1[:, ~noir].mean(1)]

    # aperçu : matière dominante, 2 m par point
    pas = 4
    piles = np.stack([paillis[::pas, ::pas]] + [p[k][::pas, ::pas] for k in COUCHES], -1)
    teintes = np.array([COULEURS_APERCU["paillis"]] + [COULEURS_APERCU[k] for k in COUCHES], np.float32)
    Image.fromarray(np.clip(piles @ teintes, 0, 255).astype(np.uint8)).save(OUT / "apercu_matieres.jpg", quality=88)

    bilan = {"description": "proportions des matières de sol du jeu, par point de 50 cm (scripts/15b_sols_du_jeu.py)",
             "emprise_l93": [bornes.left, bornes.bottom, bornes.right, bornes.top], "pas_m": tr.a,
             "lignes_colonnes": list(forme), "origine": "coin haut gauche = (x min, y max) ; ligne vers le sud",
             "couches": COUCHES, "matiere_de_fond": "paillis (matière 1 du jeu) = 1 - somme des couches",
             "parts_moyennes": {k: round(v, 3) for k, v in parts.items()},
             "couleur_1m": {"fichier": "couleur_1m.npy", "pas_m": tr.a * 2, "moyenne_rvb_dans_les_photos": moyenne_valide,
                            "hors_photo": "couleur des environs adoucie sur 40 m, puis moyenne générale",
                            "part_tiree_des_dalles_de_sol_de_l_etape_14": round(float(sol14.mean()), 3)},
             "part_couverte_par_les_photos": round(float(valide.mean()), 3),
             "seuils": {"ndvi_sol_nu": NDVI_NU, "ndvi_vert": NDVI_VERT, "ndvi_vigoureux": list(NDVI_VIGOUREUX),
                        "clarte_calcaire": list(CLARTE_CALCAIRE)},
             "pente_roche_deg": list(PENTE_ROCHE), "part_de_pentes_raides": round(part_raide, 3),
             "accotement_m": ACCOTEMENT_M, "graine": GRAINE, "duree_s": round(time.time() - t0)}
    (OUT / "sols_jeu.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(bilan["parts_moyennes"], ensure_ascii=False), f"; {bilan['duree_s']} s")


if __name__ == "__main__":
    main()
