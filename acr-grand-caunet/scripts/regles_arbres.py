"""Règle de dégagement des arbres au bord de la chaussée, commune au décor (16_paquet_unreal.py) et à la physique
(09_export_stage_ir.py), pour qu'un arbre retiré ou réduit dans l'un le soit aussi dans l'autre.

Vu en jeu le 13/11/2026 : des branches et des houppiers entiers débordaient sur la route, jusqu'à l'axe. Cause : les
arbres du jeu sont plus larges que les houppiers relevés (largeur de 0,8 à 0,93 fois la hauteur), et l'ancienne règle
ne regardait que la position du tronc (2,5 m au moins du bord).

Règle : le houppier du maillage du jeu, estimé d'après la hauteur de l'arbre, ne doit pas passer le bord de la
chaussée. Un feuillu a du feuillage jusqu'au sol : il ne dépasse pas du tout. Un grand pin n'a de branches qu'en
hauteur : il peut surplomber la route d'un mètre. Un arbre trop grand pour sa place n'est pas retiré, il est RÉDUIT
à la taille qui tient (les bords de la route réelle sont fermés par une végétation dense de 3 à 5 m) ; il n'est
retiré que s'il devrait tomber sous une taille minimale, ou si son tronc est à moins de TRONC_MIN_M du bord.
"""
TRONC_MIN_M = 1.5
MARGE_M = 0.25
LARGEUR_SUR_HAUTEUR = {"Foliage/Trees/AleppoPine": 0.80, "Foliage/Trees/BlackpineMonteCarlo": 0.61, "Foliage/Trees/Cypress": 0.54,
                       "Foliage/Trees/Olivetree": 1.26}
LARGEUR_PAR_DEFAUT = 0.92                       # feuillus du jeu (Smoketree, Blackmaple) : presque aussi larges que hauts
PINS = ("Foliage/Trees/AleppoPine", "Foliage/Trees/BlackpineMonteCarlo")
SURPLOMB_PIN_M = 1.0                            # un pin d'au moins HAUT_PIN_M peut surplomber la chaussée d'autant
HAUT_PIN_M = 9.0
HAUT_MIN_M = {"pin": 3.0, "feuillu": 1.8}
# Un feuillu réduit prend un maillage de cette famille, qui a de petits sujets (1,9 à 10 m) ; les érables du jeu ne
# descendent pas sous 13 m et seraient réduits au tiers, feuilles comprises.
FAMILLE_DES_PETITS_FEUILLUS = ("Foliage/Trees/Smoketree", "SM_Smoketree01")


def ajuste(hauteur_m, distance_au_bord_m, famille):
    """(gardé, hauteur à donner, famille du jeu, élément du jeu ou None si inchangé)."""
    if distance_au_bord_m < TRONC_MIN_M:
        return False, hauteur_m, famille, None
    pin = famille in PINS
    rapport = LARGEUR_SUR_HAUTEUR.get(famille, LARGEUR_PAR_DEFAUT)
    place = distance_au_bord_m - MARGE_M + (SURPLOMB_PIN_M if pin and hauteur_m >= HAUT_PIN_M else 0.0)
    if 0.5 * rapport * hauteur_m <= place:
        return True, hauteur_m, famille, None
    h = (distance_au_bord_m - MARGE_M) / (0.5 * rapport)          # réduit : plus de surplomb, même pour un pin
    if h < HAUT_MIN_M["pin" if pin else "feuillu"]:
        return False, hauteur_m, famille, None
    if not pin and famille not in LARGEUR_SUR_HAUTEUR and famille != FAMILLE_DES_PETITS_FEUILLUS[0] and h < 11.0:
        return True, h, FAMILLE_DES_PETITS_FEUILLUS[0], FAMILLE_DES_PETITS_FEUILLUS[1]
    return True, h, famille, None


def emprises_degagees(racine):
    """Polygones Lambert-93 (shapely) des aires et débouchés de pistes de data/reference/aires_et_pistes.json, avec leur
    matière : [(polygone, matière)]. Chaque emprise suit le bord de la chaussée, du décalage à décalage + profondeur."""
    import csv
    import json
    from pathlib import Path

    import numpy as np
    import shapely
    f = Path(racine) / "data" / "reference" / "aires_et_pistes.json"
    if not f.exists():
        return []
    with open(Path(racine) / "data" / "processed" / "chaussee_precise.csv", encoding="utf-8") as h:
        r = list(csv.DictReader(h))
    pk = np.array([float(x["pk_m"]) for x in r])
    A = np.array([[float(x["x_axe"]), float(x["y_axe"])] for x in r])
    bords = {"gauche": np.array([[float(x["x_gauche"]), float(x["y_gauche"])] for x in r]),
             "droite": np.array([[float(x["x_droite"]), float(x["y_droite"])] for x in r])}
    out = []
    for e in json.loads(f.read_text(encoding="utf-8"))["emprises"]:
        s = np.arange(e["pk_debut_m"], e["pk_fin_m"] + 0.5, 1.0)
        B = np.column_stack([np.interp(s, pk, bords[e["cote"]][:, k]) for k in (0, 1)])
        C = np.column_stack([np.interp(s, pk, A[:, k]) for k in (0, 1)])
        n = B - C
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        d0, d1 = e["decalage_m"], e["decalage_m"] + e["profondeur_m"]
        poly = shapely.Polygon(np.vstack([B + n * d0, (B + n * d1)[::-1]])).buffer(0)
        if not poly.is_empty:
            out.append((poly, e["matiere"]))
    return out + pistes_ign(racine)


# Pistes, chemins et sentiers de la BD TOPO de l'IGN dans le couloir de la route : largeur donnée à chaque nature (la
# BD TOPO ne la donne pas), et matière du sol. Position à 2,5 à 5 m près : assez pour une piste en terre dans un bois.
PISTES_IGN = {"Route empierrée": (3.6, "terre"), "Chemin": (2.6, "terre"), "Sentier": (1.1, "sentier")}


def pistes_ign(racine):
    """[(polygone Lambert-93, matière)] des pistes, chemins et sentiers de data/processed/couloir/troncon_de_route.geojson."""
    import json
    from pathlib import Path

    import shapely
    from pyproj import Transformer
    f = Path(racine) / "data" / "processed" / "couloir" / "troncon_de_route.geojson"
    if not f.exists():
        return []
    vers_l93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True).transform
    out = []
    for ft in json.loads(f.read_text(encoding="utf-8"))["features"]:
        regle = PISTES_IGN.get(ft["properties"].get("nature"))
        if not regle or ft["geometry"]["type"] != "LineString":
            continue
        xy = [vers_l93(lon, lat) for lon, lat, *_ in ft["geometry"]["coordinates"]]
        if len(xy) >= 2:
            out.append((shapely.LineString(xy).buffer(regle[0] / 2.0, cap_style="flat"), regle[1]))
    return out
