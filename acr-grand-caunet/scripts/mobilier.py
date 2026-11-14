"""Objets de bord de route posés avec des maillages du jeu (data/reference/mobilier_bord_de_route.json) : poteaux
électriques et leurs câbles, panneaux du rallye et panneaux routiers, barrières, rochers, piquets de rubalise ; et
tracés des objets en long fabriqués par le paquet (rubalises, lisses en bois, barrières de piste).

Module commun à 09_export_stage_ir.py (collisions) et 16_paquet_unreal.py (décor), pour que les deux lisent la même
liste et placent chaque objet au même endroit.

Chaque objet rendu par `objets()` est un dictionnaire : type, maillage_jeu, x, y (Lambert-93), z_sol (altitude NGF du
terrain, ou du bord de chaussée si le terrain n'est pas connu), pk, cote, dir (vecteur unitaire est / nord du sens de
la course en ce point), lacet_relatif_deg, collision (ou None), source.
"""
import csv
import json
import math
from pathlib import Path

import numpy as np

RACINE = Path(__file__).resolve().parents[1]
FICHIER = RACINE / "data" / "reference" / "mobilier_bord_de_route.json"
CREUX_MAX_M = 1.5
PORTEE_MIN_M = 30.0


class Route:
    def __init__(self):
        with open(RACINE / "data" / "processed" / "chaussee_precise.csv", encoding="utf-8") as f:
            r = list(csv.DictReader(f))
        c = lambda *k: np.array([[float(x[a]) for a in k] for x in r])          # noqa: E731
        self.pk = c("pk_m")[:, 0]
        self.A, self.G, self.D = c("x_axe", "y_axe", "z_axe"), c("x_gauche", "y_gauche", "z_gauche"), c("x_droite", "y_droite", "z_droite")
        t = np.gradient(self.A[:, :2], axis=0)
        self.T = t / np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
        self._mnt = None

    def _interp(self, tab, pk):
        return np.array([np.interp(pk, self.pk, tab[:, k]) for k in range(tab.shape[1])])

    def point(self, pk, cote, decalage):
        """(x, y, z du bord, vecteur du sens de la course) à `decalage` mètres au-delà du bord de chaussée."""
        a, e, t = self._interp(self.A, pk), self._interp(self.G if cote == "gauche" else self.D, pk), self._interp(self.T, pk)
        n = e[:2] - a[:2]
        n /= max(np.linalg.norm(n), 1e-9)
        p = e[:2] + n * decalage
        return float(p[0]), float(p[1]), float(e[2]), t / max(np.linalg.norm(t), 1e-9)

    def z_terrain(self, x, y, defaut):
        """Altitude du terrain (data/processed/mnt_couloir_1m.tif), ou `defaut` hors du modèle."""
        if self._mnt is None:
            f = RACINE / "data" / "processed" / "mnt_couloir_1m.tif"
            if f.exists():
                import rasterio
                with rasterio.open(f) as d:
                    self._mnt = (d.read(1).astype(np.float64), d.transform, d.nodata)
            else:
                self._mnt = False
        if not self._mnt:
            return defaut
        z, tr, nd = self._mnt
        c, l = (x - tr.c) / tr.a - 0.5, (y - tr.f) / tr.e - 0.5
        c0, l0 = int(np.floor(c)), int(np.floor(l))
        if c0 < 0 or l0 < 0 or c0 + 1 >= z.shape[1] or l0 + 1 >= z.shape[0]:
            return defaut
        v = z[l0:l0 + 2, c0:c0 + 2]
        if not np.isfinite(v).all() or (nd is not None and (v == nd).any()):
            return defaut
        fc, fl = c - c0, l - l0
        return float(v[0, 0] * (1 - fc) * (1 - fl) + v[0, 1] * fc * (1 - fl) + v[1, 0] * (1 - fc) * fl + v[1, 1] * fc * fl)


def charger():
    return json.loads(FICHIER.read_text(encoding="utf-8")) if FICHIER.exists() else None


def alea(pk, k):
    """Nombre entre 0 et 1, varié mais reproductible (le décor et la physique doivent tirer les mêmes)."""
    return (math.sin(pk * 12.9898 + k * 78.233) * 43758.5453) % 1.0


def _points_en_long(route, e):
    """Points (pk, côté, décalage) d'un objet en long, espacés de `pas_m` au plus. L'objet est donné soit par
    pk_debut_m, pk_fin_m, cote, decalage_m (et decalage_fin_m), soit par une liste « points » de [pk, côté, décalage]
    quand il change de côté ou de décalage en chemin."""
    pts = e.get("points") or [[e["pk_debut_m"], e["cote"], e["decalage_m"]],
                              [e["pk_fin_m"], e["cote"], e.get("decalage_fin_m", e["decalage_m"])]]
    pas, out = float(e.get("pas_m", 5.0)), []
    for (p0, c0, d0), (p1, c1, d1) in zip(pts[:-1], pts[1:]):
        if c0 != c1:                                   # d'un côté à l'autre : un seul tronçon, sans point entre deux
            n = 1
        else:
            x0, y0, _, _ = route.point(p0, c0, d0)
            x1, y1, _, _ = route.point(p1, c1, d1)
            n = max(1, int(math.ceil(max(abs(p1 - p0), math.hypot(x1 - x0, y1 - y0)) / pas)))
        for k in range(n):
            out.append((p0 + (p1 - p0) * k / n, c0, d0 + (d1 - d0) * k / n))
    out.append(tuple(pts[-1]))
    return out


def en_long(route=None):
    """Objets en long fabriqués par le paquet : pour chacun, son genre (rubalise, lisse_bois, barriere_de_piste), ses
    réglages et ses points {x, y, z_sol, pk, cote} le long de son tracé."""
    cfg = charger()
    if cfg is None:
        return []
    route = route or Route()
    out = []
    for genre in ("rubalises", "lisses"):
        for e in cfg.get(genre, []):
            pts = []
            for pk, cote, dec in _points_en_long(route, e):
                x, y, zb, _ = route.point(pk, cote, dec)
                pts.append({"x": x, "y": y, "z_sol": max(route.z_terrain(x, y, zb), zb - 1.0), "pk": float(pk), "cote": cote})
            out.append({"genre": e.get("genre", "rubalise" if genre == "rubalises" else "lisse_bois"), "points": pts,
                        **{k: v for k, v in e.items() if k not in ("points",)}})
            if genre == "rubalises" and e.get("appui", "piquets") != "piquets":
                # rubalise nouée à des troncs ou à des piquets de bois : nos arbres ne sont pas à la place des vrais,
                # donc un piquet de bois mince à chaque appui, pour que le ruban ne flotte pas en l'air
                out.append({"genre": "lisse_bois", "points": pts, "hauteur_m": float(e.get("hauteur_m", 0.9)) + 0.06,
                            "section_poteau_m": 0.06, "sans_lisse": True, "source": e.get("source", "")})
    return out


def objets(route=None):
    """Liste de tous les objets à poser, et, par ligne électrique, la liste ordonnée de ses poteaux."""
    cfg = charger()
    if cfg is None:
        return [], []
    route = route or Route()
    types = cfg["types"]
    out, lignes = [], []

    def ajoute(typ, pk, cote, dec, source, echelle=1.0, lacet_en_plus=0.0):
        t = types[typ]
        x, y, zb, d = route.point(pk, cote, dec)
        lacet = float(t.get("lacet_relatif_deg", 0)) + lacet_en_plus
        if t.get("lacet_aleatoire"):
            lacet += (pk * 137.5) % 360.0                         # orientation variée, mais reproductible
        # un objet relevé au bord de la route n'est jamais à plus d'un mètre sous la chaussée (remblai mal rendu)
        o = {"type": typ, "maillage_jeu": t["maillage_jeu"], "x": x, "y": y, "z_sol": max(route.z_terrain(x, y, zb), zb - 1.0), "z_bord": zb,
             "pk": float(pk), "cote": cote, "dir": [float(d[0]), float(d[1])], "lacet_relatif_deg": lacet,
             "echelle": float(t.get("echelle", 1.0)) * echelle, "enfoncement_m": float(t.get("enfoncement_m", 0.03)),
             "collision": t.get("collision"), "cable": t.get("cable"), "source": source}
        out.append(o)
        return o

    def pk_hors_ravin(pk, cote, dec):
        """Un poteau ne se plante pas dans un ravin : si le terrain est à plus de CREUX_MAX_M sous la chaussée (pont,
        ponceau), il est décalé le long de la ligne, de 8 m en 8 m, jusqu'à 24 m."""
        for d in (0, 8, -8, 16, -16, 24, -24):
            x, y, zb, _ = route.point(pk + d, cote, dec)
            if route.z_terrain(x, y, zb) - zb > -CREUX_MAX_M:
                return pk + d
        return pk

    for l in cfg.get("lignes_electriques", []):
        poteaux, dernier = [], -1e9
        for p in l["poteaux"]:
            dec = p.get("decalage_m", l.get("decalage_m", 2.5))
            typ = p.get("type", "poteau_beton")
            if l.get("releve"):                                  # poteau relevé sur la vidéo : posé où il a été vu
                pk = p["pk_m"]
            else:
                pk = pk_hors_ravin(p["pk_m"], l["cote"], dec)
                if pk - dernier < PORTEE_MIN_M:                  # deux poteaux décalés l'un vers l'autre : un seul
                    continue
            poteaux.append(ajoute(typ, pk, l["cote"], dec, p.get("statut") or l.get("source", "")))
            dernier = pk
        lignes.append({"nom": l["nom"], "cables": bool(l.get("cables")), "poteaux": poteaux})
    for o in cfg.get("objets", []):
        ajoute(o["type"], o["pk_m"], o["cote"], o["decalage_m"], o.get("source", ""), lacet_en_plus=float(o.get("lacet_en_plus_deg", 0)))
    # Rochers : un tronçon de bord de route donne une rangée de blocs du jeu, de taille et d'orientation variées.
    # Hauteur visée tirée entre les deux bornes relevées ; le bloc ne mord jamais sur la chaussée ; au-dessus de
    # 35 cm il a une collision (cylindre de roche, plus étroit que le bloc pour ne pas arrêter une roue qui le frôle).
    blocs = [k for k in types if k.startswith("rocher_")]
    for r in cfg.get("rochers", []):
        h0, h1 = r["hauteur_m"]
        L = float(r.get("pk_fin_m", r["pk_debut_m"]) - r["pk_debut_m"])
        n = max(1, int(round(L / r.get("pas_m", 2.4)))) if L > 0 else int(r.get("nombre", 1))
        for k in range(n):
            pk = r["pk_debut_m"] + ((k + 0.5) * L / n if L > 0 else 0.9 * k)
            # vu en jeu le 13/11/2026 : « rochers ronds identiques alignés ». L'espacement, la taille et l'enfoncement
            # varient donc d'un bloc à l'autre, et un bloc sur quatre est petit, calé contre son voisin.
            if L > 0:
                pk += (alea(pk, 7) - 0.5) * 0.8 * L / n
            h = h0 + (h1 - h0) * alea(pk, 1) ** 1.6
            if alea(pk, 8) < 0.25:
                h *= 0.45
            # un bloc du jeu n'est pas grossi ni réduit de plus du double : choix parmi ceux dont la taille convient
            # (les blocs du projet, scripts/pierres_calcaires.py, portent leurs propres bornes : « echelle_libre »)
            ok = [k for k in blocs if types[k].get("echelle_libre", (0.55, 1.9))[0] <= h / types[k]["hauteur_native_m"]
                  <= types[k].get("echelle_libre", (0.55, 1.9))[1]] or \
                [min(blocs, key=lambda k: abs(math.log(h / types[k]["hauteur_native_m"])))]
            typ = ok[int(alea(pk, 2) * len(ok)) % len(ok)]
            t = types[typ]
            ech = h / t["hauteur_native_m"]
            demi = 0.5 * t["largeur_native_m"] * ech
            dec = max(r["decalage_m"] + (alea(pk, 3) - 0.3) * r.get("profondeur_m", 0.8), demi + 0.15)
            o = ajoute(typ, pk, r["cote"], dec, r.get("source", ""), echelle=ech)
            o["enfoncement_m"] = (0.12 + 0.28 * alea(pk, 9)) * h          # un rocher sort du sol, il n'est pas posé dessus
            o["collision"] = ({"forme": "cylinder", "paroi": "PM_WallRock", "diametre_m": round(1.5 * demi, 2),
                               "hauteur_m": round(h + 0.3, 2), "enfoui_m": 0.3} if h >= 0.35 else None)
    # Piquets des rubalises : un piquet du jeu à chaque point d'appui (sauf rubalise tendue entre des arbres).
    for e in cfg.get("rubalises", []):
        if e.get("appui", "piquets") != "piquets":
            continue
        for pk, cote, dec in _points_en_long(route, e):
            ajoute("piquet_rubalise", pk, cote, dec, e.get("source", ""))
    for r in cfg.get("rangees", []):
        n = max(1, int(round((r["pk_fin_m"] - r["pk_debut_m"]) / r["pas_m"])))
        for k in range(n):
            ajoute(r["type"], r["pk_debut_m"] + (k + 0.5) * (r["pk_fin_m"] - r["pk_debut_m"]) / n, r["cote"], r["decalage_m"], r.get("source", ""))
    return out, lignes


if __name__ == "__main__":
    import collections
    o, l = objets()
    print(len(o), "objets :", dict(collections.Counter(x["type"] for x in o)))
    for x in l:
        p = x["poteaux"]
        print(f"ligne {x['nom']} : {len(p)} poteaux, portées de {min(np.hypot(p[i + 1]['x'] - p[i]['x'], p[i + 1]['y'] - p[i]['y']) for i in range(len(p) - 1)):.0f} à "
              f"{max(np.hypot(p[i + 1]['x'] - p[i]['x'], p[i + 1]['y'] - p[i]['y']) for i in range(len(p) - 1)):.0f} m ; "
              f"terrain par rapport au bord : {min(q['z_sol'] - q['z_bord'] for q in p):+.1f} à {max(q['z_sol'] - q['z_bord'] for q in p):+.1f} m")
