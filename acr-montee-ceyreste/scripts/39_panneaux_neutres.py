"""Panneaux exacts pour l'export neutre : un modèle autonome (mât + plaque texturée) par panneau relevé, posé à sa place.

Le paquet ACR garde ses substituts du jeu (triangles génériques, balises, bornes : mobilier_bord_de_route.json) ; ce
script ne sert qu'à l'export neutre (réutilisation dans un autre jeu).
Faces :
  - A15b, A1d : dessins de la signalisation française de Wikimedia Commons (auteur Roulex_45, CC BY-SA 3.0),
    téléchargés le 18/11/2026 dans data/raw/panneaux/ (non versionné) ;
  - A14, B13, B14, AB3a, J4, EB20, plaques PR, panneau temporaire : REDESSINÉS simplement ici (téléchargement refusé par
    Wikimedia : « 429 trop de requêtes ») d'après la forme réglementaire et le texte lu sur les photos.
Positions : PK et côté du relevé (releve_panoramax_2025.json, releve_clotures_2025.json), recul 0,9 m au bord de
chaussée (±5 m en long). Hauteurs : bas de plaque à 1,0 m (danger, interdiction), 2,3 m pour l'EB20 sur portique.
Sorties : modele/panneaux_neutres.glb (un maillage par panneau : <id>_mat, <id>_plaque, <id>_panonceau),
          data/processed/panneaux_neutres.json (placements, source de chaque face, licence)
Usage : python scripts/39_panneaux_neutres.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import OUT, RAW, REF, ROOT  # noqa: E402


def charger(nom, f):
    s = importlib.util.spec_from_file_location(nom, ICI / f)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


c37 = charger("c37", "37_clotures.py")
r36 = charger("r36", "36_releve_clotures.py")
MOD = ROOT / "modele"
DL = RAW / "panneaux"
COMMONS = "Wikimedia Commons, « France road sign {} », auteur Roulex_45, CC BY-SA 3.0"


def police(t):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf", t)
    except OSError:
        return ImageFont.load_default()


def triangle(pict=None, txt=None):
    im = Image.new("RGBA", (512, 460), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(256, 8), (504, 452), (8, 452)], fill=(200, 20, 30, 255))
    d.polygon([(256, 70), (446, 412), (66, 412)], fill=(250, 250, 250, 255))
    if pict == "!":
        d.rectangle([240, 170, 272, 330], fill=(20, 20, 20, 255)); d.ellipse([238, 350, 274, 386], fill=(20, 20, 20, 255))
    return im


def rond(txt, fond=(250, 250, 250)):
    im = Image.new("RGBA", (512, 512), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([4, 4, 508, 508], fill=(200, 20, 30, 255)); d.ellipse([60, 60, 452, 452], fill=fond + (255,))
    d.text((256, 256), txt, fill=(20, 20, 20, 255), font=police(150 if len(txt) <= 2 else 110), anchor="mm")
    return im


def cedez():
    im = Image.new("RGBA", (512, 460), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(8, 8), (504, 8), (256, 452)], fill=(200, 20, 30, 255))
    d.polygon([(70, 46), (442, 46), (256, 382)], fill=(250, 250, 250, 255))
    return im


def j4():
    im = Image.new("RGB", (512, 256), (30, 80, 160)); d = ImageDraw.Draw(im)
    for k in range(3):
        x = 110 + 120 * k
        d.polygon([(x, 30), (x + 60, 128), (x, 226), (x + 40, 226), (x + 100, 128), (x + 40, 30)], fill=(245, 245, 245))
    return im


def pr(txt):
    im = Image.new("RGB", (256, 320), (245, 245, 240)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 255, 110], fill=(240, 200, 20))
    d.text((128, 55), "D3", fill=(20, 20, 20), font=police(70), anchor="mm")
    d.text((128, 210), txt, fill=(20, 20, 20), font=police(110), anchor="mm")
    return im


def panonceau(txt):
    im = Image.new("RGB", (512, 160), (250, 250, 250)); d = ImageDraw.Draw(im)
    d.rectangle([4, 4, 507, 155], outline=(20, 20, 20), width=8)
    d.text((256, 80), txt, fill=(20, 20, 20), font=police(80), anchor="mm")
    return im


def panonceau_jaune(txt):
    im = Image.new("RGB", (512, 160), (240, 200, 20)); d = ImageDraw.Draw(im)
    d.text((256, 80), txt, fill=(20, 20, 20), font=police(48), anchor="mm")
    return im


def eb20():
    im = Image.new("RGB", (640, 220), (245, 245, 240)); d = ImageDraw.Draw(im)
    d.rectangle([6, 6, 633, 213], outline=(200, 20, 30), width=12)
    d.text((320, 110), "CEYRESTE", fill=(20, 20, 20), font=police(90), anchor="mm")
    d.line([(24, 200), (616, 20)], fill=(200, 20, 30), width=18)
    return im


def face_commons(code):
    p = DL / f"{code}.png"
    return (Image.open(p).convert("RGBA"), COMMONS.format(code)) if p.exists() else (None, None)


# (id, code, PK, côté, face, panonceau, largeur plaque m, bas de plaque m, nb de mâts, images)
PANNEAUX = [
    # EB20_m28 : retiré à la sixième passe (19/11/2026) ; 37_clotures.py le pose en travers avec l'EB10 au dos (doublon)
    # B14 « 50 » et B13 « 19 t » : posés depuis le 19/11/2026 par 41_carrefour_depart.py (positions par visées croisées,
    # depart.glb, qui va aussi dans l'export neutre) ; ils étaient ici aux PK -20 et 5, lus de loin
    ("A15b_86", "A15b", 86, "droite", "A15b", "4,6 km", 1.0, 1.4, 1, ["c03d3e1e", "edfd08bf"]),
    ("A1d_86", "A1d", 86.5, "droite", "A1d", "3 km", 1.0, 2.9, 0, ["c03d3e1e", "edfd08bf"]),
    ("PR5_110", "PR", 110, "gauche", "PR5", None, 0.25, 0.5, 1, ["c559b2b8"]),
    ("J4_902", "J4", 902, "gauche", "J4", None, 1.0, 0.8, 1, ["701e21a2", "a7c86442"]),
    ("J4_913", "J4", 913, "gauche", "J4", None, 1.0, 0.8, 1, ["a7c86442"]),
    ("A14_1300", "A14", 1300, "gauche", "A14", "CHAUSSÉE DÉFORMÉE", 1.0, 1.4, 1, ["(planche descente)"]),
    ("PR7_2111", "PR", 2111, "gauche", "PR7", None, 0.25, 0.5, 1, ["654381ef"]),
    ("AB3a_2938", "AB3a", 2938, "droite", "AB3a", None, 0.9, 1.3, 1, ["9f14e86c", "7a47ca44"]),
    ("PR8_3112", "PR", 3112, "gauche", "PR8", None, 0.25, 0.5, 1, ["1f995965"]),
    # sixième passe (19/11/2026), lus sur les vues de 43_chaussee_releve.py et leurs zooms
    ("PR6_1113", "PR", 1113, "gauche", "PR6", None, 0.25, 0.5, 1, ["e34f1aff"]),
    ("A15b_3672", "A15b", 3672, "gauche", "A15b", None, 1.0, 2.5, 1, ["dcde5896"]),
    ("A1c_3672", "A1c", 3672.3, "gauche", "A1c", None, 1.0, 1.4, 0, ["dcde5896"]),
    ("AB3a_3198", "AB3a", 3198, "droite", "AB3a", None, 0.9, 1.3, 1, ["7c7c6c0c", "be182a52"]),
]
# Sens de la face (sixième passe : les plaques étaient toutes posées parallèles à la route, face tournée vers la chaussée,
# alors qu'un panneau de police regarde les usagers qui arrivent) : « montee » = face aux usagers qui montent (PK
# croissants), « descente » = face aux descendants, « chemin » = face aux usagers de la voie latérale (vers l'extérieur),
# absent = parallèle à la route (plaques de PR, vues de côté sur les photos)
SENS = {"A15b_86": "montee", "A1d_86": "montee", "J4_902": "montee", "J4_913": "montee", "A14_1300": "descente",
        "AB3a_2938": "chemin", "A15b_3672": "descente", "A1c_3672": "descente", "AB3a_3198": "chemin"}


def faces():
    out = {}
    for code in ("A15b", "A1d"):
        im, src = face_commons(code)
        out[code] = (im, src) if im is not None else (triangle("!"), "redessiné (téléchargement absent)")
    # A1c (premier virage à droite) : image miroir de l'A1d (même pictogramme retourné), vu sur dcde5896
    im, src = out["A1d"]
    out["A1c"] = (im.transpose(Image.FLIP_LEFT_RIGHT), (src or "") + " ; retourné (A1c)")
    out["A14"] = (triangle("!"), "redessiné (Wikimedia : 429)")
    out["B13"] = (rond("19t"), "redessiné (Wikimedia : 429) ; texte « 19 t » lu sur la photo")
    out["B14"] = (rond("50"), "redessiné (Wikimedia : 429) ; texte « 50 » lu sur la photo")
    out["AB3a"] = (cedez(), "redessiné (Wikimedia : 429)")
    out["J4"] = (j4(), "redessiné (Wikimedia : 429)")
    out["eb20"] = (eb20(), "redessiné ; texte « CEYRESTE » lu sur la photo")
    for k in ("PR5", "PR6", "PR7", "PR8"):
        out[k] = (pr(k[2:]), "redessiné ; « D3 » et le numéro lus sur la photo (PR 8 : probable)")
    return out


def main():
    B = r36.Bord(); T = c37.Terrain()
    ref = json.loads((MOD / "repere.json").read_text(encoding="utf-8"))
    F = faces()
    mats, meshes, bilan = {}, [], []
    for (i, code, pk, cote, face, pano, larg, bas, nmats, imgs) in PANNEAUX:
        xy, _ = B.point([pk], cote, 0.9)
        P0 = xy[0]; zz = float(T.z(*P0))
        t = np.array([np.interp(pk + 1, B.pk, B.A[:, 0]) - np.interp(pk - 1, B.pk, B.A[:, 0]),
                      np.interp(pk + 1, B.pk, B.A[:, 1]) - np.interp(pk - 1, B.pk, B.A[:, 1])]); t /= np.linalg.norm(t)
        nn = np.array([[-t[1], t[0]]] * 2) * (1 if cote == "gauche" else -1)
        ax = t                                          # axe de la largeur de la plaque
        sens = SENS.get(i)
        if sens:
            nl = np.array([-t[1], t[0]]) * (1 if cote == "gauche" else -1)      # vers l'extérieur de la route
            f = {"montee": -t, "descente": t, "chemin": nl}[sens]               # vers l'usager regardé
            nn = np.array([-f] * 2)
            ax = np.array([f[1], -f[0]])                                        # gauche -> droite vu par l'usager
            ax = -ax
        im, src = F[face]
        ratio = im.size[1] / im.size[0]; H = larg * ratio
        mf = f"face_{face}"
        if mf not in mats:
            alpha = im.mode == "RGBA"
            b = io.BytesIO(); (im if alpha else im.convert("RGB")).save(b, "PNG" if alpha else "JPEG", quality=90)
            mats[mf] = {"img": b.getvalue(), "mime": "image/png" if alpha else "image/jpeg", "alpha": alpha, "double": False,
                        "rough": 0.4}
        Q = np.array([P0 - ax * larg / 2, P0 + ax * larg / 2])
        # plaque : face côté route (la face de la boîte tournée vers -n), UV 0..1 sur cette face
        pl = c37.ruban(Q, nn, -0.04, -0.02, np.full(2, zz + bas), np.full(2, zz + bas + H), ref, 1.0)
        pl["uv"] = uv_plaque(pl, ref, P0, ax, larg, zz + bas, H, cote if not sens else "face")
        meshes.append(dict(pl, name=f"{i}_plaque", mat=mf))
        haut = bas + H
        if pano:
            pim = panonceau(pano) if code != "A14" else panonceau_jaune(pano)
            mp = f"panonceau_{i}"
            b = io.BytesIO(); pim.save(b, "JPEG", quality=90)
            mats[mp] = {"img": b.getvalue(), "mime": "image/jpeg", "rough": 0.4}
            hp = larg * 0.3
            pp = c37.ruban(Q, nn, -0.04, -0.02, np.full(2, zz + bas - hp - 0.05), np.full(2, zz + bas - 0.05), ref, 1.0)
            pp["uv"] = uv_plaque(pp, ref, P0, ax, larg, zz + bas - hp - 0.05, hp, cote if not sens else "face")
            meshes.append(dict(pp, name=f"{i}_panonceau", mat=mp))
        for s in ((-larg / 2 + 0.08, larg / 2 - 0.08) if nmats == 2 else (0.0,) if nmats == 1 else ()):
            c = P0 + ax * s
            m = c37.ruban(np.array([c - ax * 0.03, c + ax * 0.03]), nn, -0.01, 0.05, np.full(2, zz - 0.4),
                          np.full(2, zz + haut + 0.05), ref, 1.0)
            meshes.append(dict(m, name=f"{i}_mat{s:+.1f}", mat="mat_vert" if code == "EB20" else "mat_galva"))
        bilan.append({"id": i, "code": code, "pk_m": pk, "cote": cote, "x_l93": round(float(P0[0]), 2),
                      "y_l93": round(float(P0[1]), 2), "z_sol_ngf": round(zz, 2), "bas_plaque_m": bas, "largeur_m": larg,
                      "panonceau": pano, "face": src, "images": imgs, "sens": SENS.get(i, "parallèle à la route"),
                      "paquet_acr": "substitut du jeu inchangé (mobilier_bord_de_route.json) ou non posé"})
    if "A1d_86" in [b["id"] for b in bilan]:
        pass
    mats["mat_vert"] = {"img": c37._jpeg(c37.tex_unie((52, 86, 58))), "mime": "image/jpeg", "rough": 0.5}
    mats["mat_galva"] = {"img": c37._jpeg(c37.tex_unie((160, 162, 165))), "mime": "image/jpeg", "rough": 0.4, "metal": 0.6}
    c37.ecrire_glb(MOD / "panneaux_neutres.glb", meshes, mats)
    (OUT / "panneaux_neutres.json").write_text(json.dumps({"note": __doc__.split("Usage")[0].strip(), "panneaux": bilan},
                                                          ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(bilan), "panneaux,", len(meshes), "maillages")


def uv_plaque(m, ref, P0, t, larg, z0, H, cote):
    """UV de la face : u le long de la plaque (gauche -> droite vu depuis la route), v de haut en bas."""
    G = m["pos"].astype(np.float64)
    x = G[:, 0] + ref["x0"]; y = -G[:, 2] + ref["y0"]; z = G[:, 1] + ref["z0"]
    s = (x - P0[0]) * t[0] + (y - P0[1]) * t[1]
    sg = {"droite": 1.0, "gauche": -1.0, "face": -1.0}[cote]   # vu depuis la route, la gauche de la plaque est vers -t (à droite)
    u = 0.5 + sg * s / larg
    v = 1.0 - (z - z0) / H
    return np.column_stack([u, v])


if __name__ == "__main__":
    main()
