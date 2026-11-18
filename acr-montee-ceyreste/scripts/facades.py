"""Géométrie des bâtiments relevés façade par façade (quatrième passe, 18-19/11/2026).

Lit data/reference/facades/<cleabs>.json (relevé sur les panoramas Panoramax 2025, voir scripts/40_facades.py et
docs/03_affinage_reel.md § 10) et construit, dans un _Lot de 12_carrefours_annexes.py (faces planes par matière, UV en
mètres, une répétition de texture tous les 2 m) :
  - les volumes exacts (l'emprise BD TOPO découpée en bandes perpendiculaires à une façade quand la photo montre deux
    corps de hauteurs différentes), murs du pied (MNT le plus bas, enterré de 0,3 m) à l'égout relevé ;
  - le toit de chaque volume (deux pans, croupes, appentis ou plat), débord, sous-face, rives, faîtage en tuiles,
    génoise (1 à 3 rangs en encorbellement) le long des égouts ;
  - les ouvertures : premier plan = baie percée dans le mur, tableau de 0,18 m, menuiserie (cadre, meneau), vitrage
    sombre ou porte au fond, appui, encadrement en léger relief, volets battants (ouverts : deux vantaux plaqués contre
    le mur ; fermés : dans la baie), volets roulants (tablier abaissé à la fraction relevée) ; plan moyen = mêmes
    éléments en aplats posés sur le mur (pas de percement) ;
  - les éléments relevés : soubassement, descentes d'eau, climatiseurs, cheminées et conduits, balcons, terrasses
    couvertes, auvents.
Une façade qu'aucune photo ne montre reçoit l'enduit relevé ailleurs, sans ouverture (rien d'inventé).

Repère du relevé : façade Fk = k-ième côté de l'emprise simplifiée (40_facades.faces) ; x en mètres depuis son coin
gauche vu de l'extérieur ; z en mètres au-dessus du « pied » = MNT LiDAR le plus bas du contour de l'emprise (les
graduations cyan des vues de 40_facades.py).
"""
from __future__ import annotations

import json
import math

import numpy as np
import shapely
from shapely.geometry import Polygon, box

EP_TOIT = 0.15
ENFOUI = 0.3
TABLEAU = 0.18          # profondeur des tableaux des baies (premier plan)

# Couleurs nommées du relevé (sRGB 0-1) : valeurs mesurées sur les panoramas quand le relevé donne « rgb », sinon ces
# teintes de référence (nuancier des menuiseries et volets courants en Provence ; nom relevé sur la photo).
COULEURS = {
    "blanc": (0.90, 0.90, 0.88), "creme": (0.88, 0.84, 0.74), "gris_clair": (0.70, 0.71, 0.70),
    "gris": (0.50, 0.51, 0.51), "anthracite": (0.22, 0.23, 0.24), "noir": (0.10, 0.10, 0.10),
    "vert": (0.36, 0.48, 0.38), "vert_pale": (0.60, 0.68, 0.58), "vert_fonce": (0.20, 0.30, 0.22),
    "bleu": (0.36, 0.50, 0.62), "bleu_pale": (0.62, 0.72, 0.78), "bleu_gris": (0.48, 0.55, 0.60),
    "lavande": (0.58, 0.56, 0.68), "bordeaux": (0.42, 0.14, 0.14), "rouge": (0.62, 0.20, 0.16),
    "marron": (0.36, 0.25, 0.17), "bois": (0.52, 0.37, 0.22), "bois_clair": (0.68, 0.53, 0.36),
    "beige": (0.78, 0.70, 0.56), "vert_armoire": (0.20, 0.36, 0.30), "ocre": (0.78, 0.58, 0.34), "jaune": (0.86, 0.74, 0.44),
    "inox": (0.70, 0.71, 0.72), "zinc": (0.58, 0.60, 0.60), "terre_cuite": (0.70, 0.40, 0.26),
}


def srgb_hex(rgb):
    """Nom stable d'une teinte d'enduit : sRGB arrondi au multiple de 8 (0-255), en hexadécimal."""
    c = [int(min(255, max(0, round(float(v) / 8) * 8))) for v in rgb]
    return "%02x%02x%02x" % tuple(c)


CLARTES = {"blanc": 0.90, "clair": 0.82, "moyen": 0.72, "soutenu": 0.62, "sombre": 0.45}


def rgb_releve(d):
    """Teinte relevée -> sRGB 0-255. d = {"rgb": [...]} (valeur posée), ou {"mesure_rgb": [...], "clarte": classe} :
    l'exposition des panoramas n'est pas calibrée (une façade blanche à l'ombre y sort à 125 sur 255) ; on garde le
    rapport des canaux mesuré (en linéaire, donc la teinte et la saturation) et l'on pose la clarté du canal le plus fort
    d'après la classe lue sur la photo (blanc 0,90, clair 0,82, moyen 0,72, soutenu 0,62, sombre 0,45 en sRGB)."""
    if d.get("rgb"):
        return [float(x) for x in d["rgb"]]
    if d.get("ortho_rgb"):
        # toit lu sur l'ortho IGN 20 cm : voile atmosphérique et compression la désaturent (tuiles rouge orangé des
        # photos rendues brun rosé) ; saturation relevée de 60 % autour de la moyenne, clarté gardée
        o = np.asarray(d["ortho_rgb"], float)
        return [round(float(x), 1) for x in np.clip(o.mean() + 1.6 * (o - o.mean()), 0, 255)]
    m = np.asarray(d["mesure_rgb"], float) / 255.0
    lin = np.where(m <= 0.04045, m / 12.92, ((m + 0.055) / 1.055) ** 2.4)
    cible = CLARTES[d.get("clarte", "clair")]
    cl = ((cible + 0.055) / 1.055) ** 2.4
    lin = lin / max(lin.max(), 1e-6) * cl
    s = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    return [round(float(x) * 255, 1) for x in s]


def couleur(nom_ou_rgb):
    if isinstance(nom_ou_rgb, (list, tuple)):
        v = np.asarray(nom_ou_rgb, float)
        return tuple(v / 255.0 if v.max() > 1.0 else v)
    return COULEURS[nom_ou_rgb]


# --- textures (calculées, sans ressource externe) ----------------------------------------------------------------
def textures(noms, m11, m12, px=512):
    """Matières des façades pour les noms demandés : enduit_<hex>, volet_<type>_<couleur>, menuiserie_<couleur>,
    porte_<couleur>, garage_<couleur>, verre, genoise, appui, faitiere, metal_<couleur>, soubassement_<hex>,
    garde_corps_<couleur>, toit_plat, tuile_<hex>."""
    n = px // 2
    out = {}
    for nom in noms:
        rng = np.random.default_rng(abs(hash(nom)) % (2 ** 31))
        g = (np.arange(n) + 0.5) / n
        uu, vv = np.meshgrid(g, g)                 # u : horizontal (m / 2), v : vertical (m / 2)
        if nom.startswith("enduit_") or nom.startswith("soubassement_"):
            t = np.array([int(nom[-6:][i:i + 2], 16) / 255 for i in (0, 2, 4)])
            if nom.startswith("soubassement_"):
                out[nom] = {"jpeg": m12.tex_enduit_vieilli(n, t, 61, nuances=0.08, sale=0.16, mousse=0.25), "rough": 0.95}
            else:
                # enduit de façade entretenu (les maisons relevées sont propres sur les photos) : grain fin, nuances faibles
                out[nom] = {"jpeg": m12.tex_enduit_vieilli(n, t, 23, nuances=0.018, sale=0.025, mousse=0.0), "rough": 0.93}
        elif nom.startswith("bardage_"):             # planches horizontales de 15 cm, joints sombres
            t = np.array([int(nom[-6:][i:i + 2], 16) / 255 for i in (0, 2, 4)])
            f = (vv * 2.0 / 0.15) % 1.0
            v = 0.06 * m11.bruit(n, rng, 1.4) - 0.35 * (f > 0.92) + 0.04 * np.sin(2 * np.pi * uu * 7)
            out[nom] = {"jpeg": m11.jpeg(t[None, None, :] * (1 + v)[..., None]), "rough": 0.9}
        elif nom.startswith("tole_"):                # tôle ondulée (ondes de 7,6 cm), patinée
            t = np.array([int(nom[-6:][i:i + 2], 16) / 255 for i in (0, 2, 4)])
            v = 0.12 * np.sin(2 * np.pi * uu * 2.0 / 0.076) + 0.08 * m11.bruit(n, rng, 1.6)
            out[nom] = {"jpeg": m11.jpeg(t[None, None, :] * (1 + v)[..., None]), "rough": 0.6}
        elif nom.startswith("tuile_"):
            t = np.array([int(nom[-6:][i:i + 2], 16) / 255 for i in (0, 2, 4)])
            out[nom] = {"jpeg": m11.jpeg(_tuiles(n, t, m11, rng)), "rough": 0.85}
        elif nom == "faitiere":
            out[nom] = {"jpeg": m11.jpeg(_tuiles(n, np.array([0.66, 0.40, 0.27]), m11, rng)), "rough": 0.85}
        elif nom.startswith("volet_"):
            _, genre, *c = nom.split("_")
            col = np.asarray(COULEURS["_".join(c)])
            v = 0.03 * m11.bruit(n, rng, 1.8)
            if genre == "persienne":                   # lames inclinées de 6 cm
                f = (vv * 2.0 / 0.06) % 1.0
                v += -0.25 * (f > 0.78) + 0.08 * (f < 0.3)
            elif genre == "roulant":                   # lames de 4 cm
                f = (vv * 2.0 / 0.04) % 1.0
                v += -0.16 * (f > 0.85)
            else:                                      # volet plein : planches verticales de 12 cm, barres
                f = (uu * 2.0 / 0.12) % 1.0
                v += -0.22 * (f > 0.93) + 0.03 * np.sin(2 * np.pi * f)
                v += -0.10 * ((vv * 2.0 % 1.0 > 0.18) & (vv * 2.0 % 1.0 < 0.24))
            out[nom] = {"jpeg": m11.jpeg(col[None, None, :] * (1 + v)[..., None]), "rough": 0.75}
        elif nom.startswith("menuiserie_") or nom.startswith("metal_") or nom.startswith("garde_corps_"):
            c = nom.split("_", 1)[1].replace("corps_", "")
            col = np.asarray(COULEURS[c])
            v = 0.02 * m11.bruit(n, rng, 2.0)
            if nom.startswith("garde_corps_"):         # barreaux verticaux de 2 cm tous les 11 cm (ajouré peint)
                f = (uu * 2.0 / 0.11) % 1.0
                fond = np.array([0.20, 0.21, 0.20])
                rgb = np.where(((f < 0.2) | ((vv * 2.0) % 1.0 < 0.04))[..., None], col[None, None, :], fond[None, None, :])
                out[nom] = {"jpeg": m11.jpeg(rgb * (1 + v)[..., None]), "rough": 0.6}
                continue
            out[nom] = {"jpeg": m11.jpeg(col[None, None, :] * (1 + v)[..., None]), "rough": 0.55 if "inox" in c else 0.7}
        elif nom.startswith("porte_"):
            col = np.asarray(COULEURS[nom[6:]])
            f = (uu * 2.0 / 0.15) % 1.0
            v = 0.03 * m11.bruit(n, rng, 1.6) - 0.18 * (f > 0.95)
            out[nom] = {"jpeg": m11.jpeg(col[None, None, :] * (1 + v)[..., None]), "rough": 0.7}
        elif nom.startswith("garage_"):
            col = np.asarray(COULEURS[nom[7:]])
            f = (vv * 2.0 / 0.5) % 1.0                 # panneaux sectionnels de 50 cm, rainures
            v = 0.02 * m11.bruit(n, rng, 2.0) - 0.20 * (np.abs(f - 0.5) > 0.47) - 0.06 * ((vv * 2.0 / 0.1) % 1.0 > 0.9)
            out[nom] = {"jpeg": m11.jpeg(col[None, None, :] * (1 + v)[..., None]), "rough": 0.6}
        elif nom == "pierre_seche":
            out[nom] = {"jpeg": m11.tex_pierre_cc0(n), "rough": 0.95}
        elif nom == "verre":
            # vitrage sombre : reflet du ciel en haut, intérieur sombre en bas, voilage clair par endroits
            rgb = np.zeros((n, n, 3)) + np.array([0.10, 0.12, 0.14])
            rgb += (0.10 * (1 - vv) ** 2)[..., None] * np.array([0.8, 0.9, 1.0])
            rgb *= (1 + 0.05 * m11.bruit(n, rng, 2.2))[..., None]
            out[nom] = {"jpeg": m11.jpeg(rgb), "rough": 0.15}
        elif nom == "genoise":
            # rangs de tuiles canal vues en bout (demi-cercles sombres) noyées dans le mortier clair ; un rang = 10 cm
            fu = (uu * 2.0 / 0.16) % 1.0
            fv = (vv * 2.0 / 0.10) % 1.0
            rang = np.floor(vv * 2.0 / 0.10)
            fu = (fu + 0.5 * (rang % 2)) % 1.0
            dx, dy = (fu - 0.5) / 0.42, (fv - 0.35) / 0.55
            tuile = (dx ** 2 + dy ** 2 < 1) & (fv > 0.35)
            creux = (dx ** 2 + dy ** 2 < 0.45) & (fv > 0.35)
            mortier = np.array([0.80, 0.76, 0.68])
            rgb = np.where(tuile[..., None], np.array([0.62, 0.34, 0.22]), mortier)
            rgb = np.where(creux[..., None], np.array([0.12, 0.08, 0.06]), rgb)
            rgb = rgb * (1 + 0.06 * m11.bruit(n, rng, 1.8))[..., None]
            out[nom] = {"jpeg": m11.jpeg(rgb), "rough": 0.9}
        elif nom == "appui":
            rgb = np.array([0.82, 0.80, 0.75]) * (1 + 0.05 * m11.bruit(n, rng, 1.8))[..., None]
            out[nom] = {"jpeg": m11.jpeg(rgb), "rough": 0.9}
        elif nom == "toit_plat":
            rgb = np.array([0.55, 0.53, 0.50]) * (1 + 0.08 * m11.bruit(n, rng, 1.2) + 0.05 * m11.flou(rng.standard_normal((n, n)), 0.6))[..., None]
            out[nom] = {"jpeg": m11.jpeg(rgb), "rough": 0.95}
        else:
            raise KeyError(nom)
    return out


def _tuiles(n, teinte, m11, rng):
    """Tuiles canal (même dessin que 12.tex_tuiles) dans la teinte relevée (sRGB 0-1)."""
    nc, nr = 10, 5
    g = (np.arange(n) + 0.5) / n
    uu, vv = np.meshgrid(g * nc, g * nr)
    rang = np.floor(vv).astype(int)
    uu = uu + 0.5 * (rang % 2)
    col = np.floor(uu).astype(int) % nc
    fu, fv = uu % 1.0, vv % 1.0
    t = np.asarray(teinte, float)
    teintes = t * (0.84 + 0.26 * rng.random((nr, nc, 1))) + 0.01 * rng.standard_normal((nr, nc, 3))
    rgb = teintes[rang % nr, col]
    rgb = rgb * (0.70 + 0.30 * np.sin(np.pi * fu))[..., None]
    rgb = rgb * (1.0 - 0.45 * np.clip((fv - 0.82) / 0.18, 0, 1) ** 1.5)[..., None]
    rgb = rgb * (1.0 + 0.07 * m11.bruit(n, rng, 1.6))[..., None]
    return rgb


def faces(P):
    """Côtés de l'emprise (anneau trigonométrique depuis le sommet le plus au sud-ouest), côtés presque alignés fusionnés."""
    R = np.asarray(shapely.orient_polygons(P).exterior.coords)[:-1, :2]
    # fusion des sommets où l'anneau tourne de moins de 8°
    keep = []
    for i in range(len(R)):
        a, b, c = R[i - 1], R[i], R[(i + 1) % len(R)]
        u, w = b - a, c - b
        ang = abs(math.degrees(math.atan2(u[0] * w[1] - u[1] * w[0], u @ w)))
        if ang > 8 or np.linalg.norm(u) < 1e-6:
            keep.append(i)
    R = R[keep]
    i0 = int(np.argmin(R[:, 0] + R[:, 1]))
    R = np.roll(R, -i0, axis=0)
    out = []
    for k in range(len(R)):
        a, b = R[k], R[(k + 1) % len(R)]
        L = float(np.linalg.norm(b - a))
        t = (b - a) / L
        n = np.array([t[1], -t[0]])                    # extérieur (anneau trigonométrique)
        cap = math.degrees(math.atan2(n[0], n[1])) % 360
        o = "N NE E SE S SO O NO".split()[int(((cap + 22.5) % 360) // 45)]
        out.append({"nom": f"F{k}", "a": a, "b": b, "long_m": round(L, 2), "normale": n, "orientation": o,
                    "cap_normale": round(cap, 1)})
    return out



# --- géométrie --------------------------------------------------------------------------------------------------
class Batisseur:
    """Construit un bâtiment relevé dans le lot `lot` (12._Lot). P : emprise L93 ; F : façades (40_facades.faces) ;
    z0 : pied (MNT le plus bas du contour) ; mnt : objet .z(x, y)."""

    def __init__(self, lot, R, P, F, z0, mnt, detail=True):
        self.lot, self.R, self.P, self.F, self.z0, self.mnt, self.detail = lot, R, P, F, z0, mnt, detail
        self.Fd = {f["nom"]: f for f in F}
        self.m_enduit = f"{R['enduit'].get('materiau', 'enduit')}_{srgb_hex(rgb_releve(R['enduit']))}"
        self.m_tuile = f"{R['toit'].get('materiau', 'tuile')}_{srgb_hex(rgb_releve(R['toit']))}" if R.get("toit") else "tuile"
        self.compte = {"ouvertures": 0, "volets": 0, "elements": 0}

    # -- outils
    def quad(self, mat, P3, n, uv):
        self.lot.face(mat, np.asarray(P3, float), np.asarray(n, float), np.asarray(uv, float))

    def pave(self, mat, o, ex, ey, ez):
        """Pavé de coin o, arêtes ex, ey, ez (vecteurs L93) : 6 faces, UV en mètres."""
        o, ex, ey, ez = (np.asarray(v, float) for v in (o, ex, ey, ez))
        for a, b, c in ((ex, ey, ez), (ey, ez, ex), (ez, ex, ey)):
            nrm = np.cross(a, b); nrm = nrm / max(np.linalg.norm(nrm), 1e-9)
            la, lb = np.linalg.norm(a), np.linalg.norm(b)
            uv = [[0, 0], [la, 0], [la, lb], [0, lb]]
            for base, s in ((o, -1), (o + c, 1)):
                self.quad(mat, [base, base + a, base + a + b, base + b], s * nrm * (1 if np.dot(nrm, c) > 0 else -1), uv)

    def cylindre(self, mat, c, r, z_bas, z_haut, k=8):
        ang = np.linspace(0, 2 * np.pi, k + 1)
        for a0, a1 in zip(ang[:-1], ang[1:]):
            p0 = np.array([c[0] + r * math.cos(a0), c[1] + r * math.sin(a0)])
            p1 = np.array([c[0] + r * math.cos(a1), c[1] + r * math.sin(a1)])
            am = (a0 + a1) / 2
            self.quad(mat, [[*p0, z_bas], [*p1, z_bas], [*p1, z_haut], [*p0, z_haut]], [math.cos(am), math.sin(am), 0],
                      [[0, 0], [r * (a1 - a0), 0], [r * (a1 - a0), z_haut - z_bas], [0, z_haut - z_bas]])

    # -- volumes
    def volumes(self):
        out = []
        for v in self.R["volumes"]:
            Pv = self.P
            b = v.get("bande")
            if b:
                f = self.Fd[b["face"]]
                a, t, n = np.asarray(f["a"]), (np.asarray(f["b"]) - np.asarray(f["a"])) / f["long_m"], np.asarray(f["normale"])
                G = float(b.get("prof", 200.0))      # profondeur de la bande depuis la façade (m)
                bande = Polygon([a + t * b["x0"] + n * 5, a + t * b["x1"] + n * 5, a + t * b["x1"] - n * G, a + t * b["x0"] - n * G])
                Pv = shapely.make_valid(self.P.intersection(bande))
                Pv = max(getattr(Pv, "geoms", [Pv]), key=lambda g: g.area)
                Pv = Polygon(np.asarray(Pv.exterior.coords)).simplify(0.05)
            out.append((v, shapely.orient_polygons(Pv)))
        # volume « reste » : l'emprise moins les autres volumes
        for k, (v, Pv) in enumerate(out):
            if v.get("reste"):
                autres = shapely.union_all([Pw.buffer(0.01) for w, Pw in out if w is not v])
                g = shapely.make_valid(self.P.difference(autres))
                g = max(getattr(g, "geoms", [g]), key=lambda x: x.area)
                out[k] = (v, shapely.orient_polygons(Polygon(np.asarray(g.exterior.coords)).simplify(0.05)))
        return out

    def construire(self):
        vols = self.volumes()
        for v, Pv in vols:
            self.volume(v, Pv, [Pw for w, Pw in vols if w is not v])
        for e in self.R.get("toiture", []):
            self.element_toit(e, vols)
        return self.compte

    def repere_toit(self, v, Pv):
        R = np.asarray(Pv.minimum_rotated_rectangle.exterior.coords)[:4]
        a, b = R[1] - R[0], R[2] - R[1]
        fa = v.get("faitage", "long")
        if fa in ("long", "court"):
            u = a if (np.linalg.norm(a) >= np.linalg.norm(b)) == (fa == "long") else b
        else:                                          # « parallele:F3 » : faîtage parallèle à la façade F3
            f = self.Fd[fa.split(":")[1]]
            u = np.asarray(f["b"]) - np.asarray(f["a"])
        u = u / np.linalg.norm(u)
        vv = np.array([-u[1], u[0]])
        S = np.asarray(Pv.exterior.coords)[:-1]
        sv, su = S @ vv, S @ u
        c = u * (su.min() + su.max()) / 2 + vv * (sv.min() + sv.max()) / 2
        return u, vv, c, (sv.max() - sv.min()) / 2, (su.max() - su.min()) / 2

    def volume(self, v, Pv, autres):
        forme = v.get("toit", "deux_pans")
        pente = float(v.get("pente", 0.30))
        debord = float(v.get("debord_m", 0.30))
        z_eg = self.z0 + float(v["egout_z"])
        u, vv, c, hw, hl = self.repere_toit(v, Pv)
        if forme == "appentis":
            fh = self.Fd[v["haut"]]
            nh = np.asarray(fh["normale"])
            s_min = min((np.asarray(Pv.exterior.coords)[:-1] - c) @ nh)

        def z_toit(XY):
            D = np.atleast_2d(XY) - c
            if forme == "deux_pans":
                return z_eg + EP_TOIT + pente * (hw - np.abs(D @ vv))
            if forme == "quatre_pans":
                return z_eg + EP_TOIT + pente * (hw - np.maximum(np.abs(D @ vv), np.abs(D @ u) - (hl - hw)))
            if forme == "appentis":
                return z_eg + EP_TOIT + pente * (D @ nh - s_min)
            return np.full(len(D), z_eg + EP_TOIT)
        self.z_toit_de = getattr(self, "z_toit_de", []) + [(Pv, z_toit)]
        ligne = (c, vv) if forme == "deux_pans" else None
        # murs (le pied enterré sous le MNT le plus bas)
        Ring = np.asarray(Pv.exterior.coords)[:-1]
        z_bas = float(self.mnt.z(Ring[:, 0], Ring[:, 1]).min()) - ENFOUI
        W = self._anneau(Ring, ligne)
        haut_plat = forme == "plat"
        if v.get("ruine"):                           # ruine de pierre sèche : murs épais, arases irrégulières, sans toit
            self.ruine(v, Ring, z_bas)
            return
        if v.get("ouvert"):                          # abri ouvert sur une face (abribus) : murs minces, intérieur vu
            self.abri(v, W, z_bas, z_toit)
            W = np.zeros((0, 2))
        for a, b in zip(W, np.roll(W, -1, axis=0)):
            L = float(np.linalg.norm(b - a))
            if L < 1e-3:
                continue
            ta, tb = z_toit(np.array([a, b])) - EP_TOIT
            if haut_plat:
                ta = tb = z_eg + float(v.get("acrotere_m", 0.3))
            n2 = np.array([(b - a)[1], -(b - a)[0]]) / L
            # mur intérieur (contre un autre volume plus haut) : pas d'ouverture, mais face posée (pignon visible)
            self.mur(a, b, z_bas, ta, tb, n2)
            # génoise le long des égouts horizontaux
            rangs = int(v.get("genoise_rangs", 0))
            if rangs and not haut_plat and abs(ta - tb) < 0.05 and abs(ta - z_eg) < 0.05 and self.detail:
                self.genoise(a, b, n2, z_eg, rangs, min(debord, 0.1 * rangs + 0.05))
        # toit
        if haut_plat:
            self.toit_plat(Pv, z_eg, v)
        else:
            self.toit(Pv, forme, u, vv, c, hw, hl, debord, z_toit, pente, v)

    def ruine(self, v, Ring, z_bas):
        ep = float(v.get("epaisseur_m", 0.5))
        h = float(v["egout_z"])
        rng = np.random.default_rng(int(abs(Ring.sum()) * 10) % (2 ** 31))
        for a, b in zip(Ring, np.roll(Ring, -1, axis=0)):
            L = float(np.linalg.norm(b - a))
            if L < 0.3:
                continue
            t = (b - a) / L
            n2 = np.array([t[1], -t[0]])
            k = max(int(L / 0.8), 1)
            for i in range(k):                       # tronçons de 0,8 m à arase inégale (± 0,25 m, pierres tombées)
                q0, q1 = a + t * L * i / k, a + t * L * (i + 1) / k
                zt = self.z0 + h + float(rng.uniform(-0.25, 0.1))
                self.pave("pierre_seche", [*q0, z_bas], [*(q1 - q0), 0], [*(-n2 * ep), 0], [0, 0, zt - z_bas])

    def abri(self, v, W, z_bas, z_toit):
        ep = 0.15
        mi = f"enduit_{srgb_hex(rgb_releve(v['enduit_interieur']))}" if v.get("enduit_interieur") else self.m_enduit
        fo = self.Fd[v["ouvert"]]
        for a, b in zip(W, np.roll(W, -1, axis=0)):
            L = float(np.linalg.norm(b - a))
            if L < 1e-3:
                continue
            t = (b - a) / L
            n2 = np.array([t[1], -t[0]])
            ta, tb = z_toit(np.array([a, b])) - EP_TOIT
            ouvert = abs((a - np.asarray(fo["a"])) @ np.asarray(fo["normale"])) < 0.3 and t @ (np.asarray(fo["b"]) - np.asarray(fo["a"])) > 0
            if ouvert:                               # piédroits aux deux bouts, linteau (bandeau) sous le toit
                for s0, s1 in ((0, 0.25), (L - 0.25, L)):
                    q0, q1 = a + t * s0, a + t * s1
                    zt = min(ta, tb)
                    self.pave(self.m_enduit, [*q0, z_bas], [*(q1 - q0), 0], [*(-n2 * ep), 0], [0, 0, zt - z_bas])
                zl = min(ta, tb)
                self.pave(v.get("bandeau", "porte_bois"), [*a, zl - 0.35], [*(b - a), 0], [*(-n2 * ep), 0], [0, 0, 0.35])
                continue
            n3 = np.array([n2[0], n2[1], 0.0])
            ai, bi = a - n2 * ep, b - n2 * ep
            self.quad(self.m_enduit, [[*a, z_bas], [*b, z_bas], [*b, tb], [*a, ta]], n3, [[0, 0], [L, 0], [L, tb - z_bas], [0, ta - z_bas]])
            self.quad(mi, [[*ai, z_bas], [*bi, z_bas], [*bi, tb], [*ai, ta]], -n3, [[0, 0], [L, 0], [L, tb - z_bas], [0, ta - z_bas]])
        for a, b in zip(W, np.roll(W, -1, axis=0)):  # éléments relevés sur les faces de l'abri (conteneur, armoire)
            L = float(np.linalg.norm(b - a))
            if L < 1e-3:
                continue
            t = (b - a) / L
            n2 = np.array([t[1], -t[0]])
            f, s0 = self.face_de(a, b, n2)
            for e in (self.R["facades"].get(f["nom"], {}).get("elements", []) if f else []):
                x = float(e.get("x", 0)) - s0
                if -0.05 <= x <= L + 0.05:
                    ta, tb = z_toit(np.array([a, b])) - EP_TOIT
                    self.element_facade(dict(e, x=x), a, t, n2, ta, tb, L)
        if v.get("banc"):                            # banc maçonné contre le fond (face opposée à l'ouverture)
            bc = v["banc"]
            fb = self.Fd[bc["face"]]
            a, b = np.asarray(fb["a"]), np.asarray(fb["b"])
            t = (b - a) / fb["long_m"]; n2 = np.asarray(fb["normale"])
            q = a + t * bc["x"] - n2 * (ep + 0.4)
            self.pave("appui", [*q, self.z0 + 0.4], [*(t * bc["l"]), 0], [*(n2 * 0.4), 0], [0, 0, 0.06])
            for s in (0.15, bc["l"] - 0.45):
                self.pave(mi, [*(q + t * s), self.z0 - 0.1], [*(t * 0.3), 0], [*(n2 * 0.4), 0], [0, 0, 0.5])

    @staticmethod
    def _anneau(R, ligne):
        if ligne is None:
            return R
        c, v = ligne
        out = []
        for a, b in zip(R, np.roll(R, -1, axis=0)):
            out.append(a)
            da, db = (a - c) @ v, (b - c) @ v
            if da * db < 0:
                out.append(a + (b - a) * da / (da - db))
        return np.array(out)

    def face_de(self, a, b, n2):
        """Façade du relevé portée par le segment [a, b] (même sens, alignée à 0,35 m) et abscisse de a sur elle."""
        t = (b - a) / np.linalg.norm(b - a)
        for f in self.F:
            fa, fb = np.asarray(f["a"]), np.asarray(f["b"])
            tf = (fb - fa) / f["long_m"]
            if t @ tf < 0.995:
                continue
            nf = np.asarray(f["normale"])
            if abs((a - fa) @ nf) > 0.35:
                continue
            s0 = float((a - fa) @ tf)
            if s0 < -0.5 or s0 > f["long_m"] + 0.5:
                continue
            return f, s0
        return None, 0.0

    def mur(self, a, b, z_bas, ta, tb, n2):
        L = float(np.linalg.norm(b - a))
        t = (b - a) / L
        n3 = np.array([n2[0], n2[1], 0.0])
        f, s0 = self.face_de(a, b, n2)
        RF = (self.R["facades"].get(f["nom"], {}) if f else {})
        mat = f"enduit_{srgb_hex(rgb_releve(RF['enduit']))}" if RF.get("enduit") else self.m_enduit
        ouv = []
        for o in RF.get("ouvertures", []):
            x0 = float(o["x"]) - s0
            if x0 >= -0.05 and x0 + float(o["l"]) <= L + 0.05:
                ouv.append(dict(o, x=max(x0, 0.05)))
        # face du mur, percée des baies (premier plan)
        poly = Polygon([(0, z_bas), (L, z_bas), (L, tb), (0, ta)])
        trous = []
        if self.detail:
            for o in ouv:
                zb = self.z0 + float(o["z"])
                r = box(o["x"], zb, o["x"] + float(o["l"]), zb + float(o["h"]))
                if poly.buffer(-0.02).contains(r):
                    trous.append(r)
        if trous:
            poly = poly.difference(shapely.union_all(trous))
        for g in getattr(poly, "geoms", [poly]):
            if g.is_empty or g.area < 1e-4:
                continue
            for tr in shapely.get_parts(shapely.constrained_delaunay_triangles(g)):
                T = np.asarray(tr.exterior.coords)[:3]
                P3 = np.column_stack([a[0] + t[0] * T[:, 0], a[1] + t[1] * T[:, 0], T[:, 1]])
                self.quad(mat, P3, n3, np.column_stack([T[:, 0], T[:, 1] - z_bas]))
        # soubassement
        sb = RF.get("soubassement") or self.R.get("soubassement")
        if sb and self.detail:
            zs = self.z0 + float(sb["h"])
            ms = f"soubassement_{srgb_hex(rgb_releve(sb))}"
            e = 0.015
            self.quad(ms, [[*(a + n2 * e), z_bas], [*(b + n2 * e), z_bas], [*(b + n2 * e), zs], [*(a + n2 * e), zs]], n3,
                      [[0, 0], [L, 0], [L, zs - z_bas], [0, zs - z_bas]])
            self.quad(ms, [[*(a + n2 * e), zs], [*(b + n2 * e), zs], [*b, zs], [*a, zs]], [0, 0, 1], [[0, 0], [L, 0], [L, e], [0, e]])
        for o in ouv:
            self.ouverture(o, a, t, n2, mat, percee=any(abs(tr.bounds[0] - o["x"]) < 1e-6 for tr in trous))
        for e in RF.get("elements", []):
            x = float(e.get("x", 0)) - s0
            if -0.05 <= x <= L + 0.05:
                self.element_facade(dict(e, x=x), a, t, n2, ta, tb, L)

    def ouverture(self, o, a, t, n2, mat_mur, percee):
        self.compte["ouvertures"] += 1
        typ = o.get("type", "fenetre")
        x0, l, h = float(o["x"]), float(o["l"]), float(o["h"])
        zb = self.z0 + float(o["z"])
        n3 = np.array([n2[0], n2[1], 0.0])
        p0 = a + t * x0
        p1 = p0 + t * l
        d = TABLEAU if percee else -0.012            # fond de la baie (en retrait), ou aplat posé sur le mur

        def P(s, z, prof):                           # point de la baie : s le long, z absolu, prof vers l'intérieur
            q = p0 + t * s - n2 * prof
            return [q[0], q[1], z]
        if percee:                                   # tableaux, linteau, appui intérieur (même enduit)
            for (s_a, z_a, s_b, z_b, nn) in ((0, zb, 0, zb + h, t), (l, zb + h, l, zb, -t)):
                self.quad(mat_mur, [P(s_a, z_a, 0), P(s_b, z_b, 0), P(s_b, z_b, d), P(s_a, z_a, d)], [nn[0], nn[1], 0],
                          [[0, 0], [h, 0], [h, d], [0, d]])
            self.quad(mat_mur, [P(0, zb + h, 0), P(l, zb + h, 0), P(l, zb + h, d), P(0, zb + h, d)], [0, 0, -1],
                      [[0, 0], [l, 0], [l, d], [0, d]])
            self.quad(mat_mur, [P(0, zb, 0), P(l, zb, 0), P(l, zb, d), P(0, zb, d)], [0, 0, 1], [[0, 0], [l, 0], [l, d], [0, d]])
        # fond : vitrage, porte, porte de garage
        men = f"menuiserie_{o.get('menuiserie', 'blanc')}"
        fond = {"porte": f"porte_{o.get('couleur', 'bois')}", "garage": f"garage_{o.get('couleur', 'blanc')}",
                "portail": f"garage_{o.get('couleur', 'blanc')}"}.get(typ, "verre")
        vol = o.get("volets", "aucun")
        etat = o.get("volet_etat", "ouvert")
        ferme = vol in ("battants", "persiennes", "plein") and etat == "ferme"
        if ferme:
            fond = f"volet_{'persienne' if vol == 'persiennes' else 'plein'}_{o.get('volet_couleur', 'vert')}"
            self.compte["volets"] += 1
        self.quad(fond, [P(0, zb, d), P(l, zb, d), P(l, zb + h, d), P(0, zb + h, d)], n3,
                  [[0, 0], [l, 0], [l, h], [0, h]])
        if fond == "verre" and self.detail:          # cadre et meneau de la menuiserie, devant le vitrage
            e = 0.06
            dm = d - 0.01 if percee else d - 0.004
            for s_a, s_b, z_a, z_b in ((0, l, zb, zb + e), (0, l, zb + h - e, zb + h), (0, e, zb, zb + h), (l - e, l, zb, zb + h)) + \
                    (((l / 2 - 0.03, l / 2 + 0.03, zb, zb + h),) if l > 0.75 and typ != "baie" else ()) + \
                    (((0, l, zb + h * 0.62, zb + h * 0.62 + 0.05),) if typ == "baie" else ()):
                self.quad(men, [P(s_a, z_a, dm), P(s_b, z_a, dm), P(s_b, z_b, dm), P(s_a, z_b, dm)], n3,
                          [[0, 0], [s_b - s_a, 0], [s_b - s_a, z_b - z_a], [0, z_b - z_a]])
        # volet roulant : tablier abaissé (fraction relevée « roulant_baisse », 0 à 1)
        if vol == "roulant":
            f = float(o.get("roulant_baisse", 0.0))
            if f > 0.02:
                dm = (d - 0.03) if percee else d - 0.006
                self.quad(f"volet_roulant_{o.get('volet_couleur', 'blanc')}",
                          [P(0, zb + h * (1 - f), dm), P(l, zb + h * (1 - f), dm), P(l, zb + h, dm), P(0, zb + h, dm)], n3,
                          [[0, 0], [l, 0], [l, h * f], [0, h * f]])
                self.compte["volets"] += 1
        # volets battants ouverts : deux vantaux (ou un si « vantaux »: 1) plaqués contre le mur, de part et d'autre
        if vol in ("battants", "persiennes", "plein") and not ferme and self.detail:
            k = int(o.get("vantaux", 2))
            mv = f"volet_{'persienne' if vol == 'persiennes' else 'plein'}_{o.get('volet_couleur', 'vert')}"
            larg = l / k
            cotes = [(-larg, 0.0), (l, l + larg)] if k == 2 else ([(l, l + larg)] if o.get("volet_cote", "droite") == "droite" else [(-larg, 0.0)])
            for s_a, s_b in cotes:
                q0, q1 = p0 + t * s_a + n2 * 0.02, p0 + t * s_b + n2 * 0.02
                self.pave(mv, [*q0, zb], [*(q1 - q0), 0], [*(n2 * 0.035), 0], [0, 0, h])
                self.compte["volets"] += 1
        # appui (saillant), encadrement
        if self.detail and typ in ("fenetre", "porte_fenetre", "baie") and o.get("appui", True):
            q0 = p0 - t * 0.05 + n2 * 0.06
            self.pave("appui", [*q0, zb - 0.05], [*(t * (l + 0.10)), 0], [*(-n2 * (0.06 + max(d, 0) + 0.0)), 0], [0, 0, 0.05])
        if self.detail and o.get("encadrement"):
            e, sv = 0.15, 0.015
            mc = f"enduit_{srgb_hex(rgb_releve(o['encadrement']))}" if isinstance(o.get("encadrement"), dict) else "appui"
            bandes = [(-e, l + e, zb + h, zb + h + e), (-e, 0, zb, zb + h), (l, l + e, zb, zb + h)]
            if typ in ("fenetre", "baie") and not o.get("appui", True):
                bandes.append((-e, l + e, zb - e, zb))
            for s_a, s_b, z_a, z_b in bandes:
                q0, q1 = p0 + t * s_a + n2 * sv, p0 + t * s_b + n2 * sv
                self.quad(mc, [[*q0, z_a], [*q1, z_a], [*q1, z_b], [*q0, z_b]], n3,
                          [[0, 0], [s_b - s_a, 0], [s_b - s_a, z_b - z_a], [0, z_b - z_a]])

    def genoise(self, a, b, n2, z_eg, rangs, saillie):
        L = float(np.linalg.norm(b - a))
        t = (b - a) / L
        for k in range(rangs):
            s = saillie * (k + 1) / rangs
            z1 = z_eg - 0.10 * k
            z0_ = z1 - 0.10
            q0, q1 = a + n2 * s, b + n2 * s
            self.quad("genoise", [[*q0, z0_], [*q1, z0_], [*q1, z1], [*q0, z1]], [n2[0], n2[1], 0],
                      [[0, 0], [L, 0], [L, 0.1], [0, 0.1]])
            self.quad("genoise", [[*a, z0_], [*b, z0_], [*q1, z0_], [*q0, z0_]], [0, 0, -1], [[0, 0], [L, 0], [L, s], [0, s]])
        del t

    def toit(self, Pv, forme, u, vv, c, hw, hl, debord, z_toit, pente, v):
        mt = self.m_tuile
        Rt = shapely.orient_polygons(Pv.buffer(debord, join_style="mitre")) if debord > 0 else Pv
        G = 4 * (hw + hl + debord + 50)
        if forme == "quatre_pans":
            dm = max(hl - hw, 0.0)
            Ra, Rb = c - u * dm, c + u * dm
            regions = [([Ra, Rb, Rb + (u + vv) * G, Ra + (-u + vv) * G], vv), ([Ra, Rb, Rb + (u - vv) * G, Ra + (-u - vv) * G], -vv),
                       ([Rb, Rb + (u + vv) * G, Rb + (u - vv) * G], u), ([Ra, Ra + (-u + vv) * G, Ra + (-u - vv) * G], -u)]
            pans = [(Rt.intersection(Polygon(q).buffer(0)), d) for q, d in regions]
        elif forme == "deux_pans":
            pans = [(Rt.intersection(Polygon([c - u * G, c + u * G, c + u * G + s * vv * G, c - u * G + s * vv * G])), s * vv)
                    for s in (1.0, -1.0)]
        else:
            nh = np.asarray(self.Fd[v["haut"]]["normale"])
            pans = [(Rt, -nh)]
        sous = v.get("sous_face", "enduit")
        ms = self.m_enduit if sous == "enduit" else (mt if sous == "tuile" else (f"menuiserie_{sous}" if sous in ("blanc", "gris_clair") else f"porte_{sous}"))
        for pan, dpan in pans:
            for g in getattr(pan, "geoms", [pan]):
                if g.is_empty or g.geom_type != "Polygon" or g.area < 1e-4:
                    continue
                for tr in shapely.get_parts(shapely.constrained_delaunay_triangles(g)):
                    T = np.asarray(tr.exterior.coords)[:3]
                    zt = z_toit(T)
                    nh = np.array([pente * dpan[0], pente * dpan[1], 1.0])
                    uvt = np.column_stack([(T - c) @ np.array([-dpan[1], dpan[0]]), (T - c) @ dpan])
                    self.quad(mt, np.column_stack([T, zt]), nh, uvt)
                    self.quad(ms, np.column_stack([T, zt - EP_TOIT]), -nh, uvt)
        Rr = self._anneau(np.asarray(Rt.exterior.coords)[:-1], (c, vv) if forme == "deux_pans" else None)
        for a, b in zip(Rr, np.roll(Rr, -1, axis=0)):
            L = float(np.linalg.norm(b - a))
            if L < 1e-3:
                continue
            ta, tb = z_toit(np.array([a, b]))
            n = np.array([(b - a)[1], -(b - a)[0], 0.0]) / L
            self.quad(mt, [[*a, ta - EP_TOIT], [*b, tb - EP_TOIT], [*b, tb], [*a, ta]], n,
                      [[0, 0], [L, 0], [L, EP_TOIT], [0, EP_TOIT]])
        # faîtage et arêtiers : tuiles faîtières (prisme de 0,12 m)
        if self.detail and forme in ("deux_pans", "quatre_pans"):
            dm = max(hl - hw, 0.0) if forme == "quatre_pans" else hl + debord
            Ra, Rb = c - u * dm, c + u * dm
            segs = [(Ra, Rb)] if dm > 0.05 else []
            if forme == "quatre_pans":
                for s_u, R_ in ((-1, Ra), (1, Rb)):
                    for s_v in (-1, 1):
                        segs.append((R_, R_ + u * s_u * (hw + debord) + vv * s_v * (hw + debord)))
            for A, B in segs:
                zA, zB = z_toit(np.array([A, B]))
                L = float(np.linalg.norm(B - A))
                if L < 0.1:
                    continue
                tt = (B - A) / L
                w = np.array([-tt[1], tt[0]])
                for s in (1, -1):
                    q0, q1 = A + w * s * 0.13, B + w * s * 0.13
                    zq0, zq1 = z_toit(np.array([q0, q1]))
                    self.quad("faitiere", [[*q0, zq0], [*q1, zq1], [*B, zB + 0.10], [*A, zA + 0.10]], [w[0] * s, w[1] * s, 1.0],
                              [[0, 0], [L, 0], [L, 0.16], [0, 0.16]])

    def toit_plat(self, Pv, z_eg, v):
        R = np.asarray(Pv.exterior.coords)[:-1]
        ac = float(v.get("acrotere_m", 0.3))
        for tr in shapely.get_parts(shapely.constrained_delaunay_triangles(Pv.buffer(-0.15, join_style="mitre"))):
            T = np.asarray(tr.exterior.coords)[:3]
            self.quad("toit_plat", np.column_stack([T, np.full(3, z_eg + 0.05)]), [0, 0, 1], T - R[0])
        # acrotère : dessus et face intérieure
        Pi = shapely.orient_polygons(Pv.buffer(-0.15, join_style="mitre"))
        for tr in shapely.get_parts(shapely.constrained_delaunay_triangles(Pv.difference(Pi))):
            T = np.asarray(tr.exterior.coords)[:3]
            self.quad("appui", np.column_stack([T, np.full(3, z_eg + ac + 0.04)]), [0, 0, 1], T - R[0])
        Ri = np.asarray(Pi.exterior.coords)[:-1]
        for a, b in zip(Ri, np.roll(Ri, -1, axis=0)):
            L = float(np.linalg.norm(b - a))
            n = -np.array([(b - a)[1], -(b - a)[0], 0.0]) / max(L, 1e-9)
            self.quad(self.m_enduit, [[*a, z_eg], [*b, z_eg], [*b, z_eg + ac], [*a, z_eg + ac]], n, [[0, 0], [L, 0], [L, ac], [0, ac]])

    def z_toit_en(self, p):
        for Pv, zf in getattr(self, "z_toit_de", []):
            if Pv.buffer(0.5).contains(shapely.Point(p)):
                return float(zf(np.array([p]))[0])
        return None

    def element_facade(self, e, a, t, n2, ta, tb, L):
        self.compte["elements"] += 1
        typ = e["type"]
        x = float(e["x"])
        p = a + t * x
        if typ == "descente":                         # descente d'eau pluviale : de l'égout au sol
            zt = ta + (tb - ta) * x / max(L, 1e-6)
            self.cylindre(f"metal_{e.get('couleur', 'zinc')}", p + n2 * 0.08, 0.045, self.z0 - 0.2, zt - 0.05, k=6)
        elif typ == "climatiseur":
            z = self.z0 + float(e.get("z", 2.5))
            self.pave(f"metal_{e.get('couleur', 'blanc')}", [*(p + n2 * 0.02), z], [*(t * 0.8), 0], [*(n2 * 0.3), 0], [0, 0, 0.55])
        elif typ == "balcon":                         # dalle + garde-corps sur les trois côtés
            x1 = x + float(e.get("l", 2.0))
            prof = float(e.get("prof", 1.0))
            z = self.z0 + float(e["z"])
            q0 = a + t * x
            self.pave(e.get("dalle", "appui"), [*q0, z - 0.15], [*(t * (x1 - x)), 0], [*(n2 * prof), 0], [0, 0, 0.15])
            gc = f"garde_corps_{e.get('couleur', 'noir')}"
            if e.get("garde_corps", "metal") == "metal":
                for A, B in ((q0 + n2 * prof, q0 + t * (x1 - x) + n2 * prof), (q0, q0 + n2 * prof), (q0 + t * (x1 - x), q0 + t * (x1 - x) + n2 * prof)):
                    self.pave(gc, [*A, z], [*(B - A), 0], [*(np.cross([0, 0, 1], [*(B - A), 0])[:2] / max(np.linalg.norm(B - A), 1e-6) * 0.02), 0], [0, 0, 1.0])
            else:                                     # garde-corps maçonné (muret enduit)
                for A, B in ((q0 + n2 * prof, q0 + t * (x1 - x) + n2 * prof), (q0, q0 + n2 * prof), (q0 + t * (x1 - x), q0 + t * (x1 - x) + n2 * prof)):
                    w = np.cross([0, 0, 1], [*(B - A), 0])[:2]
                    w = w / max(np.linalg.norm(w), 1e-6) * 0.15
                    self.pave(self.m_enduit, [*A, z], [*(B - A), 0], [*w, 0], [0, 0, 1.0])
        elif typ in ("auvent", "terrasse_couverte", "pergola"):
            l = float(e.get("l", 3.0)); prof = float(e.get("prof", 2.5)); z = self.z0 + float(e.get("z", 2.6))
            q0 = a + t * x
            toit = {"auvent": self.m_tuile, "terrasse_couverte": self.m_tuile}.get(typ, f"porte_{e.get('couleur', 'bois')}")
            pen = 0.25 if typ != "pergola" else 0.0
            for s in np.arange(0, l + 1e-6, l if typ == "auvent" else max(l / max(round(l / 3.0), 1), 0.1)):
                if typ == "auvent":
                    break
                b0 = q0 + t * min(s, l - 0.15) + n2 * (prof - 0.15)
                self.pave(f"porte_{e.get('couleur', 'bois')}" if typ == "pergola" else self.m_enduit,
                          [*b0, self.z0 + float(e.get("z_sol", 0.0)) - 0.2], [*(t * 0.15), 0], [*(n2 * 0.15), 0],
                          [0, 0, z - pen * prof - self.z0 - float(e.get("z_sol", 0.0)) + 0.2])
            # pan unique en pente vers l'extérieur
            A, B = q0, q0 + t * l
            C, D = B + n2 * (prof + 0.2), A + n2 * (prof + 0.2)
            zA, zC = z + 0.12, z - pen * (prof + 0.2) + 0.12
            if typ == "pergola":
                for s in np.arange(0.1, l, 0.6):
                    a_ = q0 + t * s
                    self.pave(toit, [*a_, z], [*(t * 0.08), 0], [*(n2 * (prof + 0.2)), 0], [0, 0, 0.12])
            else:
                self.quad(toit, [[*A, zA], [*B, zA], [*C, zC], [*D, zC]], [n2[0] * pen, n2[1] * pen, 1], [[0, 0], [l, 0], [l, prof], [0, prof]])
                self.quad(self.m_enduit if typ != "auvent" else toit, [[*A, zA - 0.1], [*B, zA - 0.1], [*C, zC - 0.1], [*D, zC - 0.1]],
                          [-n2[0] * pen, -n2[1] * pen, -1], [[0, 0], [l, 0], [l, prof], [0, prof]])
        elif typ == "boite":                           # coffret technique, boîte aux lettres
            z = self.z0 + float(e.get("z", 0.6))
            self.pave(f"metal_{e.get('couleur', 'gris')}", [*(p + n2 * float(e.get("recul", 0.01))), z], [*(t * float(e.get("l", 0.4))), 0],
                      [*(n2 * float(e.get("prof", 0.25))), 0],
                      [0, 0, float(e.get("h", 0.5))])
        else:
            raise ValueError(f"élément de façade inconnu : {typ}")

    def element_toit(self, e, vols):
        self.compte["elements"] += 1
        f = self.Fd[e["face"]]
        a, t, n = np.asarray(f["a"]), (np.asarray(f["b"]) - np.asarray(f["a"])) / f["long_m"], np.asarray(f["normale"])
        p = a + t * float(e["x"]) - n * float(e.get("recul", 1.0))
        zt = self.z_toit_en(p)
        if zt is None:
            return
        if e["type"] == "cheminee":
            l, w, h = float(e.get("l", 0.6)), float(e.get("w", 0.5)), float(e.get("h", 1.0))
            zb = zt - 0.8
            o = p - t * l / 2 - n * w / 2
            # hauteur comptée depuis le point le plus haut du toit sous la souche
            zmax = max(self.z_toit_en(q) or zt for q in (o, o + t * l, o + n * w, o + t * l + n * w))
            self.pave(self.m_enduit, [*o, zb], [*(t * l), 0], [*(n * w), 0], [0, 0, zmax + h - zb])
            self.pave(self.m_tuile, [*(o - t * 0.08 - n * 0.08), zmax + h], [*(t * (l + 0.16)), 0], [*(n * (w + 0.16)), 0], [0, 0, 0.08])
        elif e["type"] == "conduit":
            self.cylindre(f"metal_{e.get('couleur', 'inox')}", p, float(e.get("r", 0.09)), zt - 0.3, zt + float(e.get("h", 1.0)))
        elif e["type"] == "parabole":
            self.cylindre("metal_gris_clair", p, 0.3, zt + 0.5, zt + 0.55, k=10)
        else:
            raise ValueError(f"élément de toit inconnu : {e['type']}")


def materiaux_utilises(lot):
    return sorted(lot.parts.keys())


def charger_releve(f):
    return json.loads(f.read_text(encoding="utf-8"))
