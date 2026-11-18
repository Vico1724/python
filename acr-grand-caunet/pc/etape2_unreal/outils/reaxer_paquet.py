"""Réécrit les glb d'un paquet d'import (échantillon ou complet) pour une autre correspondance d'axes de l'importeur
glb d'Unreal, SANS les données sources : utile si la mire (construire_niveau.py --mire) montre que l'importeur ne fait
pas UE = 100 * (gX, gZ, gY). Python pur (bibliothèque standard), utilisable sur le PC sans rien installer.

Usage : python reaxer_paquet.py <dossier du paquet>/manifeste.json --axes Z,X,Y
Seuls les sommets, normales et l'ordre des triangles des glb changent, ainsi que manifeste.repere.axes_import_glb ;
positions des acteurs, noms et textures restent identiques. Contrôle : chaque glb est relu et ses bornes, ramenées en
repère Unreal, comparées au manifeste.
"""
import argparse
import array
import json
import os
import struct


def matrice(texte):
    M = [[0.0] * 3 for _ in range(3)]
    for i, c in enumerate(texte.replace(" ", "").split(",")):
        M[i]["XYZ".index(c.lstrip("+-").upper())] = -1.0 if c.startswith("-") else 1.0
    return M


def mul(M, v):
    return [M[i][0] * v[0] + M[i][1] * v[1] + M[i][2] * v[2] for i in range(3)]


def transposee(M):        # inverse d'une permutation signée
    return [[M[j][i] for j in range(3)] for i in range(3)]


def det(M):
    return (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1]) - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
            + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))


def lire(chemin):
    b = bytearray(open(chemin, "rb").read())
    n = struct.unpack_from("<I", b, 12)[0]
    gl = json.loads(bytes(b[20:20 + n]))
    return b, gl, 20 + n + 8


def reecrire(chemin, Mold, Mnew):
    b, gl, off = lire(chemin)
    T = [[sum(transposee(Mnew)[i][k] * Mold[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    pr = gl["meshes"][0]["primitives"][0]
    bornes = None
    for att in ("POSITION", "NORMAL"):
        a = gl["accessors"][pr["attributes"][att]]
        v = gl["bufferViews"][a["bufferView"]]
        o = off + v.get("byteOffset", 0)
        f = array.array("f")
        f.frombytes(bytes(b[o:o + a["count"] * 12]))
        lo, hi = [1e30] * 3, [-1e30] * 3
        for i in range(a["count"]):
            p = mul(T, f[3 * i:3 * i + 3])
            f[3 * i:3 * i + 3] = array.array("f", p)
            lo = [min(x, y) for x, y in zip(lo, f[3 * i:3 * i + 3])]
            hi = [max(x, y) for x, y in zip(hi, f[3 * i:3 * i + 3])]
        b[o:o + a["count"] * 12] = f.tobytes()
        if att == "POSITION":
            a["min"], a["max"] = lo, hi
            bornes = (lo, hi)
    if det(T) < 0:                                       # orientation des triangles
        a = gl["accessors"][pr["indices"]]
        v = gl["bufferViews"][a["bufferView"]]
        o = off + v.get("byteOffset", 0)
        t = array.array("H" if a["componentType"] == 5123 else "I")
        t.frombytes(bytes(b[o:o + a["count"] * t.itemsize]))
        for i in range(0, len(t), 3):
            t[i + 1], t[i + 2] = t[i + 2], t[i + 1]
        b[o:o + a["count"] * t.itemsize] = t.tobytes()
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    n_old = struct.unpack_from("<I", b, 12)[0]
    binaire = bytes(b[20 + n_old:])
    with open(chemin, "wb") as fh:
        fh.write(b"glTF" + struct.pack("<II", 2, 12 + 8 + len(js) + len(binaire)))
        fh.write(struct.pack("<II", len(js), 0x4E4F534A) + js + binaire)
    lo, hi = bornes
    return [x * 100 for x in mul(Mnew, lo)], [x * 100 for x in mul(Mnew, hi)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifeste")
    ap.add_argument("--axes", required=True)
    a = ap.parse_args()
    man = json.load(open(a.manifeste, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.manifeste))
    ancien = man["repere"]["axes_import_glb"]["valeur"]
    Mold, Mnew = matrice(ancien), matrice(a.axes)
    if abs(abs(det(Mnew)) - 1) > 1e-9:
        raise SystemExit("--axes : permutation signée attendue, p. ex. Z,X,Y ou X,-Z,Y")
    ecarts = 0
    for e in man["elements"]:
        if e["type"] != "StaticMesh" or e.get("mire"):       # la mire mesure l'importeur : jamais réécrite
            continue
        lo, hi = reecrire(os.path.join(base, *e["fichier"].split("/")), Mold, Mnew)
        if e.get("bornes_locales_cm"):
            att = e["bornes_locales_cm"]
            lo2 = [min(x, y) for x, y in zip(lo, hi)]
            hi2 = [max(x, y) for x, y in zip(lo, hi)]
            if max(max(abs(x - y) for x, y in zip(lo2, att["min"])), max(abs(x - y) for x, y in zip(hi2, att["max"]))) > 0.5:
                ecarts += 1
    man["repere"]["axes_import_glb"]["valeur"] = a.axes
    with open(a.manifeste, "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    print(f"axes {ancien} -> {a.axes} ; bornes conformes au manifeste sauf {ecarts} maillages")
    if ecarts:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
