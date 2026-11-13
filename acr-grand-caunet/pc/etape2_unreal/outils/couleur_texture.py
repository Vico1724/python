"""Couleur moyenne (et aperçu PNG) de textures du jeu, lues dans les archives installées sans rien modifier.

Sert à choisir les matières du sol et à régler les teintes d'après ce que les textures du jeu montrent vraiment, au
lieu de se fier à leur nom. Formats lus : PF_DXT1 et PF_DXT5 (les textures de couleur du jeu) ; les autres sont
signalés.

Usage : python pc/etape2_unreal/outils/couleur_texture.py <chemin /Game/... ou acr/Content/...> [...]
                                                          [--apercus DOSSIER] [--px 256]
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


def dxt_couleur(blocs):
    """blocs : (n, 8) octets d'un bloc de couleur DXT -> (n, 4, 4, 3) RVB."""
    c0 = blocs[:, 0].astype(np.int32) | (blocs[:, 1].astype(np.int32) << 8)
    c1 = blocs[:, 2].astype(np.int32) | (blocs[:, 3].astype(np.int32) << 8)

    def rvb(c):
        return np.stack([((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31], -1)

    p0, p1 = rvb(c0), rvb(c1)
    quatre = (c0 > c1)[:, None]
    pal = np.stack([p0, p1, np.where(quatre, (2 * p0 + p1) // 3, (p0 + p1) // 2), np.where(quatre, (p0 + 2 * p1) // 3, 0)], 1)
    idx = blocs[:, 4].astype(np.uint32) | (blocs[:, 5].astype(np.uint32) << 8) | (blocs[:, 6].astype(np.uint32) << 16) | (blocs[:, 7].astype(np.uint32) << 24)
    out = np.zeros((len(blocs), 4, 4, 3), np.uint8)
    for k in range(16):
        out[:, k // 4, k % 4] = pal[np.arange(len(blocs)), (idx >> np.uint32(2 * k)) & np.uint32(3)]
    return out


def decoder(donnees, w, h, fmt):
    pas = 8 if fmt == "PF_DXT1" else 16
    b = np.frombuffer(donnees, np.uint8)[: (w // 4) * (h // 4) * pas].reshape(-1, pas)
    px = dxt_couleur(b[:, pas - 8:])
    return px.reshape(h // 4, w // 4, 4, 4, 3).transpose(0, 2, 1, 3, 4).reshape(h, w, 3)


def lire(objet, a, travail):
    chemin = objet if objet.startswith("acr/") else "acr/Content/" + objet[len("/Game/"):]
    if not chemin.endswith(".uasset"):
        chemin += ".uasset"
    commun = ["--game", a.jeu, "--usmap", a.usmap]
    fj = travail / (Path(chemin).stem + ".json")
    subprocess.run([a.acr_ref, "export", chemin, "--out", str(fj), *commun], capture_output=True, text=True)
    if not fj.exists():
        return None, "absente du jeu"
    t = next((o for o in json.loads(fj.read_text(encoding="utf-8-sig")) if o["Type"].startswith("Texture")), None)
    if t is None:
        return None, "pas une texture"
    fmt = t.get("PixelFormat")
    if fmt not in ("PF_DXT1", "PF_DXT5"):
        return None, f"format {fmt} non lu"
    subprocess.run([a.acr_ref, "raw", chemin, "--out", str(travail / "brut"), *commun], capture_output=True, text=True)
    ubulk = travail / "brut" / (chemin[:-len(".uasset")] + ".ubulk")
    if not ubulk.exists():
        return None, "pas de fichier .ubulk"
    d = ubulk.read_bytes()
    mips = [m for m in t["Mips"] if "PayloadInSeperateFile" in m["BulkData"]["BulkDataFlags"]]
    m = min((m for m in mips if m["SizeX"] >= min(a.px, mips[-1]["SizeX"])), key=lambda m: m["SizeX"]) if mips else None
    if m is None:
        return None, "aucun niveau dans le .ubulk"
    off = int(m["BulkData"]["OffsetInFile"], 16)
    return decoder(d[off: off + m["BulkData"]["SizeOnDisk"]], m["SizeX"], m["SizeY"], fmt), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("textures", nargs="+")
    ap.add_argument("--apercus")
    ap.add_argument("--px", type=int, default=256)
    ap.add_argument("--jeu", default=r"Z:\acrxs\construction\vanilla")
    ap.add_argument("--travail", default=r"Z:\acrxs\unreal\relecture\textures")
    ap.add_argument("--acr-ref", default=r"Z:\acrxs\bin\acr-ref\acr-ref.exe")
    ap.add_argument("--usmap", default=r"Z:\acrxs\mappings\acr_25170642.usmap")
    a = ap.parse_args()
    travail = Path(a.travail)
    travail.mkdir(parents=True, exist_ok=True)
    out = {}
    for objet in a.textures:
        px, err = lire(objet, a, travail)
        nom = objet.rsplit("/", 1)[-1].replace(".uasset", "")
        if px is None:
            print(f"{nom:44s} {err}")
            continue
        moy = px.reshape(-1, 3).mean(0)
        lin = ((px.reshape(-1, 3) / 255.0) ** 2.2).mean(0)
        out[nom] = [round(float(v)) for v in moy]
        print(f"{nom:44s} moyenne RVB {moy[0]:5.0f} {moy[1]:5.0f} {moy[2]:5.0f}   (clarté linéaire {lin.mean():.3f}, {px.shape[1]} px)")
        if a.apercus:
            Path(a.apercus).mkdir(parents=True, exist_ok=True)
            Image.fromarray(px, "RGB").save(Path(a.apercus) / f"{nom}.png")
    return out


if __name__ == "__main__":
    main()
