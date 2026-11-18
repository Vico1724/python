"""Logo du rallye (plaque du Sainte-Baume Rallye 2026), fourni par le directeur le 18/11/2026 :
« Logo st baume/saintebaume26.webp » (500 x 225, fond transparent), copié dans ui/source/saintebaume26.webp.

Demande : « corrige la forme si besoin (supprime le rond blanc) et augmente la qualité ». Le rond blanc en haut à gauche
est l'emplacement du numéro de course des vraies plaques ; le contour de la plaque y faisait une bosse.
  1. agrandissement x4 (Lanczos), léger débruitage (médian 3 px) puis accentuation : l'image d'origine est une WebP
     compressée (aplats bruités, contours baveux) ;
  2. le rond et sa bosse disparaissent : le bord haut de l'épaule gauche (y = EPAULE) est prolongé jusqu'au dôme central,
     dont l'arc est prolongé vers la gauche (cercle ajusté sur le bord du dôme) ; ce qui dépasse devient transparent ;
  3. l'intérieur du rond et son liseré prennent le dégradé rouge-orangé du panneau gauche (même ligne, colonne x = 20) ;
  4. le liseré de la plaque (rouge sombre, filet doré) est redessiné le long du nouveau bord ;
  5. réduction au format des plaques du jeu, 485 x 218 (T_RallyWales), avec accentuation finale.
Écrit ui/T_GrandCaunetLogo.png (lu par importer_ui.py) et ui/source/saintebaume26_4x.png (contrôle).
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
UI = ROOT / "pc" / "etape2_unreal" / "ui"
SRC = UI / "source" / "saintebaume26.webp"
K = 4
EPAULE = 58.5            # px (image d'origine) : bord haut de l'épaule gauche de la plaque
ROND = (82.0, 69.0, 49.0)   # cx, cy, r (image d'origine) : le rond blanc (pixels blancs x 33-131, y 21-117), mesuré le 18/11
LISERE_ROND = 6.0           # px : liseré rouge autour du rond
PANNEAU_X = 117             # px : bord droit du panneau rouge-orangé sous le rond ; la photo commence à droite


def main():
    src = Image.open(SRC).convert("RGBA")
    a0 = np.asarray(src).astype(float)
    cx, cy, r = ROND
    H0, W0 = a0.shape[:2]
    # bord du dôme central (x de 140 à 225) : cercle ajusté, prolongé vers la gauche
    al0 = a0[..., 3]
    xs = np.arange(140, 226)
    ys = np.array([np.argmax(al0[:, x] > 128) for x in xs], float)
    A = np.column_stack([xs, ys, np.ones_like(xs)])
    c, *_ = np.linalg.lstsq(A, -(xs ** 2 + ys ** 2), rcond=None)
    dx, dy = -c[0] / 2, -c[1] / 2
    dr = np.sqrt(dx ** 2 + dy ** 2 - c[2])

    big = src.resize((W0 * K, H0 * K), Image.LANCZOS)
    rgb = big.convert("RGB").filter(ImageFilter.MedianFilter(3)).filter(ImageFilter.UnsharpMask(radius=3, percent=90, threshold=2))
    a = np.dstack([np.asarray(rgb).astype(float), np.asarray(big)[..., 3].astype(float)])
    H, W = a.shape[:2]
    Y, X = np.mgrid[0:H, 0:W] / K
    # nouveau bord haut, à gauche du dôme : épaule, puis arc du dôme
    with np.errstate(invalid="ignore"):
        dome = dy - np.sqrt(np.maximum(dr ** 2 - (X - dx) ** 2, 0))
    bord = np.where(X < dx - dr, EPAULE, np.minimum(EPAULE, dome))
    zone = X < 150                                                   # seule la partie gauche change
    dedans_rond = (X - cx) ** 2 + (Y - cy) ** 2 <= (r + LISERE_ROND) ** 2   # rond + son liseré
    # 2. transparent au-dessus du nouveau bord
    a[..., 3] = np.where(zone & (Y < bord - 0.5), 0, np.where(zone & (Y < bord + 0.5), a[..., 3] * (Y - bord + 0.5), a[..., 3]))
    # 3. intérieur du rond : à gauche de PANNEAU_X, le panneau (dégradé vertical de la colonne x = 20, plus l'écart
    #    horizontal relevé entre les logos FFSA et Ligue) ; à droite, la photo, reprise en miroir de la bande voisine
    lignes = slice(143 * K, 150 * K)          # bande libre entre le logo FFSA (y 118-140) et celui de la Ligue (y 152-172)
    c20 = a[:, 20 * K, :3]
    ecart = np.median(a[lignes, :, :3] - a[lignes, 20 * K:20 * K + 1, :3], axis=0)
    rempl = dedans_rond & (Y >= bord)
    pan = rempl & (X <= PANNEAU_X)
    for k in range(3):
        a[..., k] = np.where(pan, c20[:, None, k] + ecart[None, :, k], a[..., k])
    photo = rempl & (X > PANNEAU_X)
    bordD = int((cx + r + LISERE_ROND + 1) * K)
    yy, xx = np.nonzero(photo)
    xm = np.clip(2 * bordD - xx, 0, W - 1)
    a[yy, xx, :3] = a[yy, xm, :3]
    a[..., 3] = np.where(rempl, 255, a[..., 3])
    # 4. liseré le long du nouveau bord (dans la zone modifiée seulement) : rouge sombre puis filet doré
    d = Y - bord
    neuf = zone & (dedans_rond | (Y < EPAULE + 6)) & (X > 4) & (X <= PANNEAU_X + 30)
    for (d0, d1), c3 in (((0, 2.6), (150, 28, 38)), ((2.6, 3.5), (214, 178, 96))):
        m = neuf & (d >= d0) & (d < d1)
        for k in range(3):
            a[..., k] = np.where(m, c3[k], a[..., k])
    big = Image.fromarray(np.clip(a, 0, 255).astype("uint8"), "RGBA")
    big.save(UI / "source" / "saintebaume26_4x.png")
    fin = big.resize((485, 218), Image.LANCZOS)
    rgb = fin.convert("RGB").filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=2))
    fin = Image.merge("RGBA", (*rgb.split(), fin.split()[3]))
    fin.save(UI / "T_GrandCaunetLogo.png")
    print(f"écrit : {UI / 'T_GrandCaunetLogo.png'} (485 x 218) et {UI / 'source' / 'saintebaume26_4x.png'} ({W} x {H})")


if __name__ == "__main__":
    main()
