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
HAUT_MIN_M = {"pin": 3.0, "feuillu": 1.2}          # 1,8 jusqu'au 13/11/2026 ; 1,2 pour le premier rang des haies
# Un feuillu réduit prend un maillage de cette famille, qui a de petits sujets (1,9 à 10 m) ; les érables du jeu ne
# descendent pas sous 13 m et seraient réduits au tiers, feuilles comprises.
# Jusqu'au 13/11/2026 : Smoketree. Relevé du quatrième essai : ses feuillages sont teintés de mauve et de rose (c'est un
# arbre à perruque), ce qui ne ressemble à rien sur cette route. Le Boxthorn du jeu est un arbuste dense, vert sombre.
FAMILLE_DES_PETITS_FEUILLUS = ("Foliage/Trees/Boxthorn", "SM_Boxthorn01")
FAMILLE_D_AUTOMNE = "Foliage/Trees/BlackmapleMonteCarlo"      # feuillage jaune en jeu : tient lieu de chêne pubescent en novembre
PART_D_AUTOMNE, HAUT_AUTOMNE_M = 0.30, 8.0


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


# --- choix du maillage d'après sa forme -------------------------------------------------------------------
# Constat du 13/11/2026 (pc/etape2_unreal/outils/profils_arbres.py) : la largeur supposée ci-dessus (0,8 fois la hauteur
# pour un pin) est fausse pour plusieurs maillages. À l'import, un pin reçoit au hasard l'un des quinze pins d'Alep du
# jeu : SM_AleppoPine06 fait 9 m de haut pour 13 m de large, feuillu jusqu'au sol ; SM_AleppoPine11 est un pin parasol
# sans rien sous 5 m. Près de la route, le maillage est donc choisi ICI, d'après sa forme mesurée :
#   - sous DEGAGE_M (hauteur d'une voiture et de son champ de vision), rien ne dépasse le bord de chaussée ;
#   - au-dessus, le houppier peut surplomber la route de SURPLOMB_MAX_M au plus, comme les pins de la route réelle ;
#   - l'arbre garde sa hauteur si un maillage tient ; sinon il est réduit pas à pas jusqu'à ce qu'un maillage tienne.
DEGAGE_M = 4.5
SURPLOMB_MAX_M = 3.0
ECHELLES = (0.6, 1.5)                           # échelles admises, comme scripts_editeur/attribution.py
# Le Boxthorn est un arbuste : réduit au tiers, il fait un buisson de 1,3 m plausible. Sans cela, aucun sujet ne tient à
# moins de 1,6 m du bord, et les haies du km 5,1 à 5,4 restaient à 3 à 5 m de la chaussée (relevé du sixième essai).
ECHELLES_PAR_FAMILLE = {"Foliage/Trees/Boxthorn": (0.3, 1.5)}
TRONC_MIN_HAIE_M = 0.8                          # pied d'un sujet de haie (décor seul, sans tronc dans la physique)
BANDE_M = 14.0                                  # au-delà de cette distance au bord, aucun maillage n'atteint la route
_PROFILS = None


def profils():
    """{famille : {maillage : {haut_m, rayons_m}}} de pc/etape2_unreal/releves/profils_arbres.json, ou {} s'il manque."""
    global _PROFILS
    if _PROFILS is None:
        import json
        from pathlib import Path
        f = Path(__file__).resolve().parents[1] / "pc" / "etape2_unreal" / "releves" / "profils_arbres.json"
        _PROFILS = {}
        if f.exists():
            for fam, ms in json.loads(f.read_text(encoding="utf-8"))["familles"].items():
                _PROFILS[fam] = {n: p for n, p in ms.items() if p["haut_m"] >= 1.5}
    return _PROFILS


def famille_rendue(essence, famille, hauteur_m=None, cle=None):
    """Famille du jeu qui rend vraiment l'arbre. Les chênes verts sont rendus en Boxthorn ; une part des grands (la
    reconnaissance montre beaucoup de chênes jaunis ou roux au bord de la route) prend un feuillu d'automne."""
    import zlib
    if essence == "chêne vert" and famille in ("Foliage/Trees/BlackmapleMonteCarlo", "Foliage/Trees/Smoketree", FAMILLE_DES_PETITS_FEUILLUS[0]):
        if hauteur_m is not None and hauteur_m >= HAUT_AUTOMNE_M and zlib.crc32(f"automne:{cle}".encode("utf-8")) % 100 < 100 * PART_D_AUTOMNE:
            return FAMILLE_D_AUTOMNE
        return FAMILLE_DES_PETITS_FEUILLUS[0]
    return famille


def tient(profil, echelle, distance_au_bord_m):
    """Vrai si le maillage, à cette échelle, ne dépasse pas le bord sous DEGAGE_M ni de plus de SURPLOMB_MAX_M au-dessus."""
    h = profil["haut_m"] * echelle
    for i, r in enumerate(profil["rayons_m"]):
        depasse = r * echelle - (distance_au_bord_m - MARGE_M)
        if depasse > 0 and (0.1 * i * h < DEGAGE_M or depasse > SURPLOMB_MAX_M):
            return False
    return True


def choisir(hauteur_m, distance_au_bord_m, famille, cle, tronc_min_m=None):
    """(gardé, hauteur, famille du jeu, maillage, échelle). Maillage et échelle valent None quand le choix est laissé à
    l'import (formes non relevées) ; `cle` rend le tirage reproductible. tronc_min_m : distance minimale du pied au
    bord (TRONC_MIN_M par défaut ; TRONC_MIN_HAIE_M pour les sujets de haie du décor)."""
    import math
    import random
    import zlib
    if distance_au_bord_m < (TRONC_MIN_M if tronc_min_m is None else tronc_min_m):
        return False, hauteur_m, famille, None, None
    if famille not in profils():
        g, h, fam, elt = ajuste(hauteur_m, distance_au_bord_m, famille)
        return g, h, fam, elt, None
    rng = random.Random(zlib.crc32(str(cle).encode("utf-8")))
    pin = famille in PINS
    essais = [(famille, hauteur_m)]
    if not pin and famille != FAMILLE_DES_PETITS_FEUILLUS[0]:
        essais.append((FAMILLE_DES_PETITS_FEUILLUS[0], min(hauteur_m, 11.0)))      # grand feuillu sans place : petit feuillu
    for fam, h0 in essais:
        h = h0
        while h >= HAUT_MIN_M["pin" if pin else "feuillu"]:
            tous = [(n, h / p["haut_m"], p) for n, p in sorted(profils()[fam].items())]
            e0, e1 = ECHELLES_PAR_FAMILLE.get(fam, ECHELLES)
            admis = [x for x in tous if e0 <= x[1] <= e1]
            if not admis and not pin and fam != FAMILLE_DES_PETITS_FEUILLUS[0]:
                break                                       # érable ou olivier trop petit ou trop grand : petit feuillu à la place
            if not admis:                                   # aucune taille du jeu ne convient : les plus proches, comme à l'import
                mieux = min(abs(math.log(x[1])) for x in tous)
                admis = [x for x in tous if abs(math.log(x[1])) <= mieux + math.log(1.25)]
            bons = [(n, e) for n, e, p in admis if tient(p, e, distance_au_bord_m)]
            if bons:
                n, e = rng.choice(bons)
                return True, h, fam, n, e
            h *= 0.93
    return False, hauteur_m, famille, None, None


def rocailles(racine):
    """[(polygone Lambert-93, hauteur maxi)] des talus de rocaille de data/reference/parois_rocheuses.json (genre « eboulis ») :
    bande le long du bord de chaussée, du pied du talus jusqu'où sa hauteur le porte sur une pente de 40 degrés."""
    import csv
    import json
    import math
    from pathlib import Path

    import numpy as np
    import shapely
    f = Path(racine) / "data" / "reference" / "parois_rocheuses.json"
    if not f.exists():
        return []
    with open(Path(racine) / "data" / "processed" / "chaussee_precise.csv", encoding="utf-8") as h:
        r = list(csv.DictReader(h))
    pk = np.array([float(x["pk_m"]) for x in r])
    A = np.array([[float(x["x_axe"]), float(x["y_axe"])] for x in r])
    bords = {"gauche": np.array([[float(x["x_gauche"]), float(x["y_gauche"])] for x in r]),
             "droite": np.array([[float(x["x_droite"]), float(x["y_droite"])] for x in r])}
    out = []
    for e in json.loads(f.read_text(encoding="utf-8"))["parois"]:
        if e["genre"] != "eboulis":
            continue
        s = np.arange(e["pk_debut_m"], e["pk_fin_m"] + 0.5, 1.0)
        if len(s) < 2:
            continue
        B = np.column_stack([np.interp(s, pk, bords[e["cote"]][:, k]) for k in (0, 1)])
        C = np.column_stack([np.interp(s, pk, A[:, k]) for k in (0, 1)])
        n = B - C
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        d0 = max(float(e["decalage_m"]) - 0.3, 0.3)
        d1 = d0 + max(1.5, max(e["hauteur_m"]) / math.tan(math.radians(40.0)) + 0.8)
        poly = shapely.Polygon(np.vstack([B + n * d0, (B + n * d1)[::-1]])).buffer(0)
        if not poly.is_empty:
            out.append((poly, float(max(e["hauteur_m"]))))
    return out


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


# --- nature du bord de route (data/reference/bords_vegetation.json) -------------------------------------
PART_GARDEE_EN_ZONE_OUVERTE = 0.25
BANDE_OUVERTE_M = 16.0
_BORDS = {}


def bords_vegetation(racine):
    """[(genre, pk de début, pk de fin, côté)] : zones où la nature du bord de route a été relevée sur la reconnaissance."""
    import json
    from pathlib import Path
    cle = str(racine)
    if cle not in _BORDS:
        f = Path(racine) / "data" / "reference" / "bords_vegetation.json"
        _BORDS[cle] = [(z["genre"], float(z["pk"][0]), float(z["pk"][1]), z["cote"])
                       for z in json.loads(f.read_text(encoding="utf-8"))["zones"]] if f.exists() else []
    return _BORDS[cle]


def genre_du_bord(racine, pk, cote):
    """Genre relevé pour ce PK et ce côté (« gauche » ou « droite »), ou None : règle générale."""
    for genre, p0, p1, c in bords_vegetation(racine):
        if p0 <= pk <= p1 and c in (cote, "les deux"):
            return genre
    return None


def bandes_ouvertes(racine):
    """Polygone Lambert-93 (ou None) des bords « ouverts » : du bord de chaussée à BANDE_OUVERTE_M, du côté relevé."""
    import csv
    from pathlib import Path

    import numpy as np
    import shapely
    zones = [z for z in bords_vegetation(racine) if z[0] == "ouvert"]
    if not zones:
        return None
    with open(Path(racine) / "data" / "processed" / "chaussee_precise.csv", encoding="utf-8") as h:
        r = list(csv.DictReader(h))
    pk = np.array([float(x["pk_m"]) for x in r])
    A = np.array([[float(x["x_axe"]), float(x["y_axe"])] for x in r])
    bords = {"gauche": np.array([[float(x["x_gauche"]), float(x["y_gauche"])] for x in r]),
             "droite": np.array([[float(x["x_droite"]), float(x["y_droite"])] for x in r])}
    polys = []
    for _, p0, p1, c in zones:
        s = np.arange(p0, p1 + 0.5, 1.0)
        C = np.column_stack([np.interp(s, pk, A[:, k]) for k in (0, 1)])
        for cote in (("gauche", "droite") if c == "les deux" else (c,)):
            B = np.column_stack([np.interp(s, pk, bords[cote][:, k]) for k in (0, 1)])
            n = B - C
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
            poly = shapely.Polygon(np.vstack([B, (B + n * BANDE_OUVERTE_M)[::-1]])).buffer(0)
            if not poly.is_empty:
                polys.append(poly)
    return shapely.union_all(polys) if polys else None


def garde_en_zone_ouverte(cle):
    """Vrai pour l'arbre sur quatre qui reste dans une zone ouverte ; `cle` rend le tirage reproductible."""
    import zlib
    return zlib.crc32(f"ouvert:{cle}".encode("utf-8")) % 100 < 100 * PART_GARDEE_EN_ZONE_OUVERTE
