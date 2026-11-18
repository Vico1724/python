"""Images du rallye propre au Grand Caunet (demande du directeur, 17/11/2026 ; docs/19_rallye_propre.md).

- T_GrandCaunetLogo.png (485 x 218, fond transparent) : depuis le build 24, la plaque officielle du rallye fournie par le
  directeur (logo_sainte_baume.py). Au build 22 : la plaque du rallye, au format des plaques du jeu
  (T_RallyWales : 485 x 218). Demande du directeur (17/11/2026) : les logos du rallye de la Sainte-Baume, pris dans
  son roadbook (Roadbook SBRC 2026.pdf, bandeau d'en-tête des pages, image et masque recomposés :
  ui/source/bandeau_roadbook_sbr2026.png) : titre « SAINTE BAUME RALLYE », logo de l'ASA Marseille Provence
  Métropole, logos de la Ligue PACA et de la FFSA ; bande bleue au nom de la spéciale.
- T_GrandCaunetFond.png (406 x 737) : le fond vertical du lieu, au format de T_WalesRally. Photographie aérienne IGN
  (BD ORTHO 20 cm, data/raw/ortho_20cm.tif, licence ouverte Etalab) recadrée sur la route au PK 4 080, à 0,5 m par pixel.

Usage : python pc/etape2_unreal/outils/images_rallye.py   (écrit dans pc/etape2_unreal/ui/)
"""
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "pc" / "etape2_unreal" / "ui"
POLICES = [Path(r"C:\Windows\Fonts\bahnschrift.ttf"), Path(r"C:\Windows\Fonts\arialbd.ttf")]
BLANC, BLEU, VERT, OCRE, GRIS = (244, 244, 240), (28, 74, 140), (30, 92, 52), (214, 170, 96), (60, 62, 66)


def police(taille, gras=True):
    for p in POLICES:
        if p.exists():
            f = ImageFont.truetype(str(p), taille)
            if p.name == "bahnschrift.ttf":
                try:
                    f.set_variation_by_name("Bold" if gras else "Regular")
                except (OSError, ValueError):
                    pass
            return f
    return ImageFont.load_default()


BANDEAU = OUT / "source" / "bandeau_roadbook_sbr2026.png"
# régions du bandeau (1574 x 167), relevées le 17/11/2026 : (x0, y0, x1, y1)
ZONES = {"asa": (0, 8, 188, 162), "sainte_baume": (236, 6, 832, 72), "rallye": (860, 6, 1141, 72),
         "ligue": (1134, 74, 1324, 162), "ffsa": (1326, 70, 1574, 162)}


def morceau(nom, hauteur=None, largeur=None):
    im = Image.open(BANDEAU).convert("RGB").crop(ZONES[nom])
    a = np.asarray(im).astype(int)
    encre = a.sum(2) < 720                                   # rogne le blanc autour
    ys, xs = np.nonzero(encre)
    im = im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    k = (hauteur / im.height) if hauteur else (largeur / im.width)
    im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    # le blanc du bandeau devient transparent (la plaque est blanche)
    a = np.asarray(im.convert("RGB")).astype(float)
    alpha = np.clip((765 - a.sum(2)) / 60.0, 0, 1) * 255
    return Image.fromarray(np.dstack([a, alpha]).astype("uint8"), "RGBA")


def plaque():
    s = 4                                              # dessin à 4x puis réduit (bords lisses)
    W, H = 485 * s, 218 * s
    forme = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(forme)
    d.rounded_rectangle((6 * s, 40 * s, W - 6 * s, H - 6 * s), radius=26 * s, fill=255)
    d.ellipse((150 * s, 4 * s, 335 * s, 120 * s), fill=255)                 # dôme de la plaque
    fond = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    # bas de la plaque : bande bleue au nom de la spéciale, sous un liseré tricolore
    bande = Image.new("L", (W, H), 0)
    ImageDraw.Draw(bande).rectangle((0, 176 * s, W, H), fill=255)
    fond.paste(Image.new("RGBA", (W, H), (200, 30, 40, 255)), (0, 0), bande.filter(ImageFilter.MaxFilter(17)))
    fond.paste(Image.new("RGBA", (W, H), (255, 255, 255, 255)), (0, 0), bande.filter(ImageFilter.MaxFilter(9)))
    fond.paste(Image.new("RGBA", (W, H), (20, 40, 150, 255)), (0, 0), bande)
    dd = ImageDraw.Draw(fond)
    b = dd.textbbox((0, 0), "ES  LE GRAND CAUNET", font=police(25 * s))
    dd.text(((W - (b[2] - b[0])) / 2 - b[0], 197 * s - (b[3] - b[1]) / 2 - b[1]), "ES  LE GRAND CAUNET", font=police(25 * s), fill=(255, 255, 255))
    # logos et titre du roadbook
    asa = morceau("asa", hauteur=118 * s)
    fond.alpha_composite(asa, (16 * s, 50 * s))
    sb = morceau("sainte_baume", largeur=300 * s)
    x0 = 16 * s + asa.width + 12 * s
    xc = (x0 + W - 14 * s) // 2
    fond.alpha_composite(sb, (xc - sb.width // 2, 54 * s))
    ra = morceau("rallye", hauteur=sb.height)
    fond.alpha_composite(ra, (xc - ra.width // 2, 54 * s + sb.height + 10 * s))
    lg = morceau("ligue", hauteur=40 * s)
    ff = morceau("ffsa", hauteur=40 * s)
    y = 176 * s - 8 * s - 40 * s
    xl = xc - (lg.width + 14 * s + ff.width) // 2
    fond.alpha_composite(lg, (xl, y))
    fond.alpha_composite(ff, (xl + lg.width + 14 * s, y))
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im.paste(fond, (0, 0), forme)
    bord = forme.filter(ImageFilter.MaxFilter(9)).point(lambda v: 255 if v else 0)
    contour = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    contour.paste(Image.new("RGBA", (W, H), (150, 152, 156, 255)), (0, 0), bord)
    contour.alpha_composite(im)
    return contour.resize((485, 218), Image.LANCZOS)


def fond_aerien(pk_m=4080.0, decalage_nord_m=70.0):
    import rasterio
    from rasterio.windows import from_bounds
    with open(ROOT / "data" / "processed" / "chaussee_precise.csv", encoding="utf-8") as f:
        r = list(csv.DictReader(f))
    pk = np.array([float(x["pk_m"]) for x in r])
    A = np.array([[float(x["x_axe"]), float(x["y_axe"])] for x in r])
    cx, cy = A[np.argmin(abs(pk - pk_m))]
    cy += decalage_nord_m
    w, h = 406 * 0.5, 737 * 0.5
    with rasterio.open(ROOT / "data" / "raw" / "ortho_20cm.tif") as src:
        win = from_bounds(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, src.transform)
        a = src.read([1, 2, 3], window=win, out_shape=(3, 737, 406), boundless=True, resampling=rasterio.enums.Resampling.average)
    im = Image.fromarray(np.moveaxis(a, 0, -1).astype("uint8"))
    im = ImageEnhance.Brightness(im).enhance(1.35)
    im = ImageEnhance.Contrast(im).enhance(1.1)
    return im.convert("RGBA")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # logo : la plaque officielle du Sainte-Baume Rallye 2026 fournie par le directeur le 18/11/2026, sans le rond du
    # numéro (logo_sainte_baume.py) ; plaque() (logos du bandeau du roadbook) reste pour mémoire (build 22)
    import importlib.util
    spec = importlib.util.spec_from_file_location("logo_sainte_baume", Path(__file__).with_name("logo_sainte_baume.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.main()
    fond_aerien().save(OUT / "T_GrandCaunetFond.png")
    for n in ("T_GrandCaunetLogo.png", "T_GrandCaunetFond.png"):
        print(f"écrit : {OUT / n} ({Image.open(OUT / n).size[0]} x {Image.open(OUT / n).size[1]})")


if __name__ == "__main__":
    main()
