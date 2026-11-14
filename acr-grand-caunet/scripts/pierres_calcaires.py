"""Pierres et blocs calcaires fabriqués par le projet, à poser en instances avec notre roche claire (MI_GC_Roche).

Pourquoi : vu en jeu le 13/11/2026 au soir (sixième version), les pierres du jeu semées sur les accotements et les talus
(Props/GreeceProps/GreElaSmallStones) et les rochers du jeu posés au bord (Props/Nature) sortent en blocs RONDS
GRIS-ROSÉ. Leur matériau (MI_GreElaSmallLimestone) porte une texture beige rosé assombrie et désaturée : rien à voir
avec la pierraille calcaire blanche et anguleuse de la reconnaissance, et il ne peut pas être réglé (on ne livre
aucun matériau du jeu). D'où des pierres à nous : enveloppes convexes anguleuses, facettes franches, tirées au sort
avec une graine fixe (les formes ne changent pas d'une fabrication à l'autre).

Chaque forme fait 1 m de long à l'échelle 1 : l'échelle d'une instance est donc sa longueur en mètres. Le pivot est
au centre de la base ; la pose enfonce la pierre d'une part de sa hauteur.

  Stone A à D : pierraille des accotements et des talus de rocaille (dossier Props/Stones, masquée au loin) ;
  Bloc A à C  : blocs et affleurements isolés du bord de route (dossier Props/Blocks, toujours visibles, avec collision
                dans la physique : scripts/mobilier.py).

Usage : python scripts/pierres_calcaires.py            affiche les dimensions
        python scripts/pierres_calcaires.py --types    met à jour les types « rocher_* » de mobilier_bord_de_route.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import ConvexHull

RACINE = Path(__file__).resolve().parents[1]
DOSSIER_UE = "/Game/Environments/GrandCaunet/Props"
UV_M = 2.5                         # même dépliage que les parois (ROCHE["uv_m"] dans 16_paquet_unreal.py)
# nom : (longueur, largeur, hauteur) en mètres, nombre de sommets tirés, graine, part de cube (0 : galet, 1 : pavé)
FORMES = {
    "StoneA": {"dim": (1.0, 0.78, 0.55), "n": 13, "graine": 11, "cube": 0.55, "dossier": "Stones"},     # caillou trapu
    "StoneB": {"dim": (1.0, 0.72, 0.30), "n": 12, "graine": 12, "cube": 0.70, "dossier": "Stones"},     # dalle
    "StoneC": {"dim": (1.0, 0.52, 0.42), "n": 11, "graine": 13, "cube": 0.45, "dossier": "Stones"},     # éclat allongé
    "StoneD": {"dim": (1.0, 0.90, 0.78), "n": 15, "graine": 14, "cube": 0.75, "dossier": "Stones"},     # bloc
    "BlocA": {"dim": (1.0, 0.86, 0.36), "n": 22, "graine": 21, "cube": 0.70, "dossier": "Blocks"},      # affleurement plat
    "BlocB": {"dim": (1.0, 0.80, 0.62), "n": 24, "graine": 22, "cube": 0.65, "dossier": "Blocks"},      # bloc
    "BlocC": {"dim": (1.0, 0.74, 0.92), "n": 24, "graine": 23, "cube": 0.60, "dossier": "Blocks"},      # bloc dressé
    # Poteau électrique en béton. Essais des 13 et 14/11/2026 : aucun poteau du jeu ne convient (jumelés en A, bois sombre
    # épais, mât bleu-gris, puis « caissons bleu-noir d'un mètre de large » avec SM_MonPylonB11) ; les vrais sont des
    # poteaux de béton gris clair, fins, à petite traverse. Celui-ci est le nôtre : fût effilé de 8,2 m (24 x 20 cm au
    # pied, 15 x 13 cm en tête), traverse d'1,1 m à 7,65 m, trois isolateurs. « dim » : largeur de la traverse,
    # épaisseur du fût, hauteur. Il prend la matière claire de la roche, faute de mieux : à l'échelle d'un poteau elle
    # donne un gris-beige uni et rugueux.
    "PoteauBeton": {"dim": (1.1, 0.24, 8.2), "genre": "poteau", "dossier": "Poles"},
}


def nom_ue(nom):
    return f"SM_GrandCaunet{nom}"


def chemin_ue(nom):
    return f"{DOSSIER_UE}/{FORMES[nom]['dossier']}/{nom_ue(nom)}"


def forme(nom):
    """Renvoie (positions, normales, uv, triangles, couleurs) : positions en mètres, repère glTF du projet (Y vers le
    haut), base à Y = 0 ; un sommet par coin de triangle (facettes franches)."""
    f = FORMES[nom]
    if f.get("genre") == "poteau":
        return _poteau(f)
    rng = np.random.default_rng(f["graine"])
    n = f["n"]
    # directions bien réparties (spirale de Fibonacci) puis bousculées
    i = np.arange(n) + 0.5
    phi, th = np.arccos(1 - 2 * i / n), np.pi * (1 + 5 ** 0.5) * i
    d = np.column_stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)])
    d += rng.normal(0.0, 0.16, d.shape)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    # de la sphère vers le pavé : une pierre cassée a des faces planes et des arêtes
    d = d / np.abs(d).max(1, keepdims=True) ** f["cube"]
    d *= rng.uniform(0.82, 1.0, (n, 1))
    p = d * (np.array(f["dim"]) / 2.0)
    # assise : une pierre posée est plus large à la base qu'au sommet (sans cela, certaines semblaient en porte-à-faux)
    p[:, :2] *= (1.0 - 0.30 * (p[:, 2] / f["dim"][2]))[:, None]
    hull = ConvexHull(p)
    p = p[hull.vertices]
    hull = ConvexHull(p)
    # recadrage exact sur les dimensions voulues, base à 0
    lo, hi = p.min(0), p.max(0)
    p = (p - (lo + hi) / 2) / (hi - lo) * np.array(f["dim"])
    p[:, 2] -= p[:, 2].min()
    g = p[:, [0, 2, 1]]                                   # glTF du projet : Y vers le haut
    tri = hull.simplices.copy()
    centre = g.mean(0)
    a, b, c = g[tri[:, 0]], g[tri[:, 1]], g[tri[:, 2]]
    fn = np.cross(b - a, c - a)
    envers = np.einsum("ij,ij->i", fn, (a + b + c) / 3 - centre) < 0
    tri[envers] = tri[envers][:, [0, 2, 1]]
    fn[envers] *= -1.0
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    pos = g[tri].reshape(-1, 3)
    nrm = np.repeat(fn, 3, axis=0)
    # dépliage : projection sur le plan le plus proche de la face
    axe = np.abs(fn).argmax(1)
    autres = np.array([[1, 2], [0, 2], [0, 1]])[axe]
    uv = np.take_along_axis(g[tri], np.repeat(autres[:, None, :], 3, axis=1), axis=2).reshape(-1, 2) / UV_M
    uv += np.repeat(rng.uniform(0.0, 1.0, (len(tri), 2)), 3, axis=0)
    usure = np.repeat(rng.uniform(0.22, 0.58, len(tri)), 3)
    coul = np.column_stack([(255 * usure).astype(np.uint8), np.zeros(len(pos), np.uint8), np.full(len(pos), 255, np.uint8),
                            np.full(len(pos), 255, np.uint8)])
    return pos, nrm, uv, np.arange(len(pos)).reshape(-1, 3), coul


def _boite(lo, hi, haut=None):
    """Pavé (glTF du projet, Y vers le haut) : 8 coins, ou un tronc de pyramide si `haut` donne la demi-section du dessus.
    Renvoie les 12 triangles (36 sommets), normales vers l'extérieur comprises."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    if haut is None:
        hx0, hx1, hz0, hz1 = x0, x1, z0, z1
    else:
        cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
        hx0, hx1, hz0, hz1 = cx - haut[0], cx + haut[0], cz - haut[1], cz + haut[1]
    c = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1], [hx0, y1, hz0], [hx1, y1, hz0], [hx1, y1, hz1], [hx0, y1, hz1]])
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    tri = np.array([[q[0], q[1], q[2]] for q in faces] + [[q[0], q[2], q[3]] for q in faces])
    pos = c[tri].reshape(-1, 3, 3)
    fn = np.cross(pos[:, 1] - pos[:, 0], pos[:, 2] - pos[:, 0])
    envers = np.einsum("ij,ij->i", fn, pos.mean(1) - c.mean(0)) < 0
    pos[envers] = pos[envers][:, [0, 2, 1]]
    fn[envers] *= -1.0
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    return pos.reshape(-1, 3), np.repeat(fn, 3, axis=0)


def _poteau(f):
    """Poteau de béton : fût effilé, traverse, trois isolateurs. Même sortie que forme()."""
    larg, ep, h = f["dim"]
    pieces = [_boite((-ep / 2, 0.0, -0.10), (ep / 2, h, 0.10), haut=(0.075, 0.065)),            # fût
              _boite((-larg / 2, h - 0.62, -0.04), (larg / 2, h - 0.52, 0.04))]                 # traverse
    for x in (-larg / 2 + 0.06, 0.0, larg / 2 - 0.06):
        pieces.append(_boite((x - 0.035, h - 0.52, -0.035), (x + 0.035, h - 0.36, 0.035)))      # isolateurs
    pos = np.vstack([p_ for p_, _ in pieces])
    nrm = np.vstack([n_ for _, n_ in pieces])
    axe = np.abs(nrm).argmax(1)
    autres = np.array([[1, 2], [0, 2], [0, 1]])[axe]
    uv = np.take_along_axis(pos, autres, axis=1) / UV_M
    coul = np.column_stack([np.full(len(pos), 90, np.uint8), np.zeros(len(pos), np.uint8), np.full(len(pos), 255, np.uint8),
                            np.full(len(pos), 255, np.uint8)])
    return pos, nrm, uv, np.arange(len(pos)).reshape(-1, 3), coul


def type_poteau():
    """Entrée « types » de mobilier_bord_de_route.json pour le poteau de béton du projet."""
    larg, ep, h = FORMES["PoteauBeton"]["dim"]
    return {"maillage_jeu": chemin_ue("PoteauBeton"), "maillage_du_projet": True,
            "description": f"poteau de béton du projet (scripts/pierres_calcaires.py) : fût effilé de {h} m, traverse de {larg} m, trois isolateurs",
            "lacet_relatif_deg": 90, "enfoncement_m": 0.0, "echelle": 1.0,
            "bornes_cm": {"min": [int(-50 * larg), -12, 0], "max": [int(50 * larg), 12, int(100 * h)]},
            "collision": {"forme": "cylinder", "paroi": "PM_WallConcrete", "diametre_m": 0.25, "hauteur_m": 3.5, "enfoui_m": 0.4},
            "cable": {"hauteur_m": round(h - 0.4, 2), "ecarts_m": [round(-larg / 2 + 0.06, 2), 0.0, round(larg / 2 - 0.06, 2)]}}


def type_mobilier(nom):
    """Entrée « types » de mobilier_bord_de_route.json pour un bloc (dimensions natives lues par scripts/mobilier.py)."""
    L, l, h = FORMES[nom]["dim"]
    return {"maillage_jeu": chemin_ue(nom), "maillage_du_projet": True,
            "description": f"bloc calcaire du projet (scripts/pierres_calcaires.py), {h} m de haut pour 1 m de long à l'échelle 1",
            "lacet_relatif_deg": 0, "lacet_aleatoire": True, "enfoncement_m": 0.05, "hauteur_native_m": h,
            "largeur_native_m": round((L + l) / 2, 2), "echelle_libre": [0.4, 2.6],
            "bornes_cm": {"min": [-50, int(round(-50 * l)), 0], "max": [50, int(round(50 * l)), int(round(100 * h))]}}


def main():
    for nom in FORMES:
        pos, nrm, uv, tri, coul = forme(nom)
        d = pos.max(0) - pos.min(0)
        print(f"{nom_ue(nom):24s} {len(tri):3d} faces  {d[0]:.2f} x {d[2]:.2f} x {d[1]:.2f} m (long, large, haut)  {chemin_ue(nom)}")
    if "--types" in sys.argv:
        f = RACINE / "data" / "reference" / "mobilier_bord_de_route.json"
        o = json.loads(f.read_text(encoding="utf-8"))
        anciens = {k: v for k, v in o["types"].items() if k.startswith("rocher_")}
        if anciens and not all(v.get("maillage_du_projet") for v in anciens.values()):
            o["types_de_rochers_du_jeu_abandonnes"] = {
                "pourquoi": "vus en jeu le 13/11/2026 au soir : rochers ronds et sombres du jeu, alors que la reconnaissance montre des blocs "
                            "et des affleurements de calcaire blanc ; remplacés par les blocs du projet (scripts/pierres_calcaires.py)",
                "types": anciens}
        o["types"] = {k: v for k, v in o["types"].items() if not k.startswith("rocher_")}
        for lettre, nom in zip("abc", ("BlocA", "BlocB", "BlocC")):
            o["types"][f"rocher_{lettre}"] = type_mobilier(nom)
        ancien = o["types"].get("poteau_beton", {})
        if not ancien.get("maillage_du_projet"):
            o.setdefault("types_de_poteaux_du_jeu_abandonnes", {})["poteau_beton"] = ancien
        o["types"]["poteau_beton"] = type_poteau()
        f.write_text(json.dumps(o, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("types rocher_a à rocher_c mis à jour dans", f.name)


if __name__ == "__main__":
    main()
