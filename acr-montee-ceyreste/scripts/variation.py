"""Variation de teinte par sommet (sixième passe, 19/11/2026) contre la répétition des textures.

Demande de l'utilisateur (transmise par le coordinateur, mots exacts) : « des textures encore trop répétitives ». Une
texture de 2 à 4 m répétée le long d'un mur de 60 m, d'une façade ou d'un toit montre son motif. Ici, chaque sommet
reçoit une couleur (glTF COLOR_0, multipliée par la texture) tirée d'un bruit de valeur lisse à deux échelles, calculé
sur sa position : la teinte varie lentement à l'intérieur d'un même élément, sans couture, et deux éléments voisins
diffèrent. Écrit par les écrivains glb de 11_route_ouvrages.py et 37_clotures.py (donc 11, 12, 31, 37, 41, 44) pour
les matières listées dans REGLES. Aperçu (15) et export neutre (33) ; le paquet Unreal garde ses couleurs de sommet (16
ne lit pas COLOR_0 : les matières du jeu s'en servent pour autre chose).
"""
import numpy as np

# préfixe de matière -> (amplitude de l'assombrissement, échelle large m, échelle fine m, désaturation)
REGLES = [
    ("pierre", 0.16, 7.0, 1.6, 0.25), ("mur_", 0.16, 7.0, 1.6, 0.25), ("enduit", 0.07, 6.0, 1.8, 0.0),
    ("soubassement", 0.10, 4.0, 1.0, 0.0), ("beton", 0.08, 6.0, 1.5, 0.0), ("chaperon", 0.08, 5.0, 1.2, 0.0),
    ("tuile", 0.13, 5.0, 1.2, 0.2), ("faitiere", 0.10, 4.0, 1.0, 0.0), ("genoise", 0.08, 4.0, 1.0, 0.0),
    ("haie", 0.22, 4.0, 1.0, 0.0), ("feuillage", 0.22, 3.0, 0.8, 0.0), ("lierre", 0.18, 3.0, 0.8, 0.0),
    ("vigne", 0.18, 3.0, 0.8, 0.0), ("enrobe", 0.07, 18.0, 3.5, 0.0), ("dalle", 0.06, 6.0, 1.5, 0.0),
    ("bordure", 0.08, 5.0, 1.2, 0.0), ("enrobe_rouge", 0.10, 6.0, 1.5, 0.3),
]


def regle(mat):
    m = str(mat)
    best = None
    for p, *r in REGLES:
        if m.startswith(p) and (best is None or len(p) > len(best[0])):
            best = (p, *r)
    return best[1:] if best else None


def _hash(ix, iy, iz, graine):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ (iz.astype(np.int64) * 83492791) ^ graine
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFF).astype(np.float64) / 65535.0


def bruit(p, ech, graine=0):
    """Bruit de valeur 3D lisse (0..1) aux points p (n, 3), cellule de « ech » m."""
    q = np.asarray(p, np.float64) / ech
    i = np.floor(q).astype(np.int64)
    f = q - i
    f = f * f * (3 - 2 * f)
    out = np.zeros(len(q))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out += w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, graine)
    return out


def couleurs(pos, mat):
    """COLOR_0 (n, 3) float32 dans [0, 1] pour une matière, ou None si elle n'est pas concernée."""
    r = regle(mat)
    if r is None or len(pos) == 0:
        return None
    amp, grand, fin, desat = r
    p = np.asarray(pos, np.float64)
    v = 0.65 * bruit(p, grand, 11) + 0.35 * bruit(p, fin, 23)          # 0..1, moyenne 0,5
    lum = 1.0 - amp * np.clip((v - 0.25) / 0.5, 0, 1)                  # de 1 à 1 - amp
    # légère dérive de teinte (pierres plus ocre ou plus grises, tuiles plus ou moins rouges)
    t = bruit(p, grand * 1.7, 37) - 0.5
    c = np.column_stack([lum * (1 + 0.04 * t), lum, lum * (1 - 0.04 * t - desat * 0.04 * t)])
    return np.clip(c, 0, 1).astype(np.float32)
