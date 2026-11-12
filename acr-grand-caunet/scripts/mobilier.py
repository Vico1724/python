"""Objets de bord de route posés avec des maillages du jeu (data/reference/mobilier_bord_de_route.json) : poteaux
électriques et leurs câbles, panneaux du rallye, barrières, haie.

Module commun à 09_export_stage_ir.py (collisions) et 16_paquet_unreal.py (décor), pour que les deux lisent la même
liste et placent chaque objet au même endroit.

Chaque objet rendu par `objets()` est un dictionnaire : type, maillage_jeu, x, y (Lambert-93), z_sol (altitude NGF du
terrain, ou du bord de chaussée si le terrain n'est pas connu), pk, cote, dir (vecteur unitaire est / nord du sens de
la course en ce point), lacet_relatif_deg, collision (ou None), source.
"""
import csv
import json
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


def objets(route=None):
    """Liste de tous les objets à poser, et, par ligne électrique, la liste ordonnée de ses poteaux."""
    cfg = charger()
    if cfg is None:
        return [], []
    route = route or Route()
    types = cfg["types"]
    out, lignes = [], []

    def ajoute(typ, pk, cote, dec, source):
        t = types[typ]
        x, y, zb, d = route.point(pk, cote, dec)
        o = {"type": typ, "maillage_jeu": t["maillage_jeu"], "x": x, "y": y, "z_sol": route.z_terrain(x, y, zb), "z_bord": zb,
             "pk": float(pk), "cote": cote, "dir": [float(d[0]), float(d[1])], "lacet_relatif_deg": float(t.get("lacet_relatif_deg", 0)),
             "collision": t.get("collision"), "source": source}
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
            pk = pk_hors_ravin(p["pk_m"], l["cote"], l["decalage_m"])
            if pk - dernier < PORTEE_MIN_M:                      # deux poteaux décalés l'un vers l'autre : un seul
                continue
            poteaux.append(ajoute("poteau", pk, l["cote"], l["decalage_m"], p.get("statut") or l.get("source", "")))
            dernier = pk
        lignes.append({"nom": l["nom"], "cables": bool(l.get("cables")), "poteaux": poteaux})
    for o in cfg.get("objets", []):
        ajoute(o["type"], o["pk_m"], o["cote"], o["decalage_m"], o.get("source", ""))
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
