"""Relit le conteneur du décor (zz_gc_gc_P.*) avec les archives du jeu, hors du jeu, et contrôle ce qui peut l'être.

À lancer après cuire_et_empaqueter.ps1, avant d'installer. Ne modifie rien dans le jeu : il construit une vue de
liens (archives d'origine + mod de l'étape 1 + notre conteneur) et la lit avec acr-ref (CUE4Parse).

Contrôles :
  1. le conteneur ne contient que notre dossier et la cellule du niveau hôte : aucun factice n'est livré ;
  2. le niveau : nombre de maillages posés, d'instances, maillages du jeu désignés ;
  3. sol « façon jeu » : chaque variante MI_Sol_* a pour parent la variante de terrain du jeu, ne porte aucune
     permutation propre, et désigne ses deux masques et la carte ; les masques sont des textures virtuelles au même
     format que ceux du jeu (DXT5, dalles de 128 + 4), et leur contenu relu est celui du fichier source ;
  4. les maillages de sol et d'enrobé ont une couleur de sommet nulle ;
  5. les herbes disparaissent avec la distance et ne portent pas d'ombre, comme celles du jeu.
Ce script ne prouve pas l'affichage en jeu.

Usage : python pc/etape2_unreal/outils/relire_decor.py [--conteneur Z:/acrxs/unreal/dist] [--paquet paquet_unreal]
Sortie : pc/etape2_unreal/releves/relecture_decor.json ; code 1 si un contrôle échoue.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

KIT = Path(__file__).resolve().parents[1]
RACINE = KIT.parents[1]
CELLULE = "1LS8FPM8JIMX697U3QIPKC01K"
MASQUE_DU_JEU = "acr/Content/Environments/MonteCarloS1Bollene/TerrainMasks/T_Bollene1001_M1.uasset"


def dxt5(data, w, h):
    b = np.frombuffer(data, dtype=np.uint8).reshape(h // 4, w // 4, 16)
    out = np.zeros((h // 4, w // 4, 4, 4, 4), dtype=np.uint8)
    a0, a1 = b[..., 0].astype(np.int32), b[..., 1].astype(np.int32)
    bits = np.zeros(b.shape[:2], dtype=np.uint64)
    for i in range(6):
        bits |= b[..., 2 + i].astype(np.uint64) << np.uint64(8 * i)
    pal = np.zeros(b.shape[:2] + (8,), dtype=np.int32)
    pal[..., 0], pal[..., 1] = a0, a1
    gt = a0 > a1
    for i in range(1, 7):
        pal[..., 1 + i] = np.where(gt, ((7 - i) * a0 + i * a1) // 7, 0)
    for i in range(1, 5):
        pal[..., 1 + i] = np.where(gt, pal[..., 1 + i], ((5 - i) * a0 + i * a1) // 5)
    pal[..., 6] = np.where(gt, pal[..., 6], 0)
    pal[..., 7] = np.where(gt, pal[..., 7], 255)
    c0 = b[..., 8].astype(np.int32) | (b[..., 9].astype(np.int32) << 8)
    c1 = b[..., 10].astype(np.int32) | (b[..., 11].astype(np.int32) << 8)

    def rgb(c):
        return np.stack([((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31], -1)

    p0, p1 = rgb(c0), rgb(c1)
    cp = np.stack([p0, p1, (2 * p0 + p1) // 3, (p0 + 2 * p1) // 3], -2)
    ci = (b[..., 12].astype(np.uint32) | (b[..., 13].astype(np.uint32) << 8) | (b[..., 14].astype(np.uint32) << 16)
          | (b[..., 15].astype(np.uint32) << 24))
    for k in range(16):
        y, x = divmod(k, 4)
        ia = ((bits >> np.uint64(3 * k)) & np.uint64(7)).astype(np.int64)
        ic = ((ci >> np.uint32(2 * k)) & np.uint32(3)).astype(np.int64)
        out[:, :, y, x, 3] = np.take_along_axis(pal, ia[..., None], -1)[..., 0]
        out[:, :, y, x, :3] = np.take_along_axis(cp, ic[..., None, None].repeat(3, -1), -2)[..., 0, :]
    return out.transpose(0, 2, 1, 3, 4).reshape(h, w, 4)


def morton(x, y):
    r = 0
    for i in range(12):
        r |= ((x >> i) & 1) << (2 * i) | ((y >> i) & 1) << (2 * i + 1)
    return r


def lire_masque_vt(ubulk, vt):
    """Niveau le plus fin d'une texture virtuelle DXT5 à une couche, d'après sa description (VTData de CUE4Parse)."""
    d = Path(ubulk).read_bytes()
    dalle, bord, taille = vt["TileSize"], vt["TileBorderSize"], vt["Width"]
    n, t = taille // dalle, dalle + 2 * bord
    octets = (t // 4) ** 2 * 16
    debut = int(vt["Chunks"][vt["ChunkIndexPerMip"][0]]["BulkData"]["OffsetInFile"], 16) + vt["BaseOffsetPerMip"][0]
    img = np.zeros((taille, taille, 4), dtype=np.uint8)
    for y in range(n):
        for x in range(n):
            o = debut + morton(x, y) * octets
            img[y * dalle:(y + 1) * dalle, x * dalle:(x + 1) * dalle] = dxt5(d[o:o + octets], t, t)[bord:-bord, bord:-bord]
    return img


def resume_vt(j):
    t = j[0]
    vt = t.get("VTData") or {}
    def court(v):                    # « TextureAddress::TA_Clamp » (jeu) et « TA_Clamp » (cuisson avec versions)
        return v.split("::")[-1] if isinstance(v, str) else v

    return {"format": t.get("PixelFormat"), "virtuelle": bool(t["Properties"].get("VirtualTextureStreaming")),
            "compression": court(t["Properties"].get("CompressionSettings")), "srgb": t["Properties"].get("SRGB", True),
            "adressage": court(t["Properties"].get("AddressX")), "couches": vt.get("NumLayers"), "dalle": vt.get("TileSize"),
            "bordure": vt.get("TileBorderSize"), "types_de_couche": vt.get("LayerTypes"),
            "codecs": sorted({c for ch in vt.get("Chunks", []) for c in ch.get("CodecType", [])}),
            "octets_par_dalle": vt.get("TileDataOffsetPerLayer")}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--conteneur", default=r"Z:\acrxs\unreal\dist")
    ap.add_argument("--nom", default="zz_gc_gc_P")
    ap.add_argument("--paquet", default=str(RACINE / "paquet_unreal"))
    ap.add_argument("--vue-du-jeu", default=r"Z:\acrxs\construction\controle\full", help="archives d'origine + mod de l'étape 1 (liens)")
    ap.add_argument("--travail", default=r"Z:\acrxs\unreal\relecture")
    ap.add_argument("--acr-ref", default=r"Z:\acrxs\bin\acr-ref\acr-ref.exe")
    ap.add_argument("--usmap", default=r"Z:\acrxs\mappings\acr_25170642.usmap")
    a = ap.parse_args()
    trav = Path(a.travail)
    shutil.rmtree(trav, ignore_errors=True)
    vue, seul = trav / "vue" / "acr" / "Content" / "Paks", trav / "seul" / "acr" / "Content" / "Paks"
    vue.mkdir(parents=True)
    seul.mkdir(parents=True)
    for f in (Path(a.vue_du_jeu) / "acr" / "Content" / "Paks").iterdir():
        os.link(f, vue / f.name)
    for f in Path(a.conteneur).glob(a.nom + ".*"):
        os.link(f, vue / f.name)
        os.link(f, seul / f.name)
    env = {**os.environ, "DOTNET_SYSTEM_GLOBALIZATION_INVARIANT": "1"}

    def ref(*args, jeu=vue):
        r = subprocess.run([a.acr_ref, *args, "--game", str(jeu.parents[2]), "--usmap", a.usmap], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        return r.stdout

    def exporter(chemin):
        return json.loads(ref("export", chemin))

    erreurs, bilan = [], {}
    liste = [l.strip() for l in ref("list", jeu=seul).splitlines() if l.strip().startswith("acr/")]
    hors = [l for l in liste if "/Environments/GrandCaunet/" not in l and CELLULE not in l]
    bilan["conteneur"] = {"fichiers": len(liste), "hors_de_notre_dossier": len(hors)}
    if hors:
        erreurs.append(f"fichiers livrés hors de notre dossier : {hors[:3]}")

    # niveau
    ref("export-many", "--filter", f"^acr/Content/Levels/WalesS4HafrenSouth/_Generated_/{CELLULE}\\.umap$", "--out", str(trav / "niveau"))
    niv = max(trav.joinpath("niveau").rglob("*.umap.json"), key=lambda f: f.stat().st_size)
    j = json.loads(niv.read_text(encoding="utf-8-sig"))
    smc = [o for o in j if o["Type"] == "StaticMeshComponent" and (o.get("Properties") or {}).get("StaticMesh")]
    hism = [o for o in j if "InstancedStaticMeshComponent" in o["Type"] and (o.get("Properties") or {}).get("StaticMesh")]
    par = {}
    for o in hism:
        par[o["Properties"]["StaticMesh"]["ObjectPath"].split(".")[0]] = len(o.get("PerInstanceSMData", []))
    man = json.loads((Path(a.paquet) / "manifeste.json").read_text(encoding="utf-8"))
    attendu_m = sum(1 for e in man["elements"] if e["type"] == "StaticMesh" and e.get("acteur"))
    attendu_i = sum(e["nombre"] for e in man["elements"] if e["type"] == "InstanceGroup")
    bilan["niveau"] = {"maillages_poses": len(smc), "attendus": attendu_m, "instances": sum(par.values()), "attendues": attendu_i,
                       "composants_d_instances": len(hism),
                       "instances_hors_vegetation": {k.rsplit("/", 1)[1]: v for k, v in par.items() if "/Foliage/" not in k}}
    if len(smc) != attendu_m:
        erreurs.append(f"{len(smc)} maillages posés pour {attendu_m} attendus")
    if sum(par.values()) != attendu_i:
        erreurs.append(f"{sum(par.values())} instances pour {attendu_i} attendues")
    # herbes : distances de disparition et ombre, comme dans le jeu
    # (par dossier : pour les buissons, l'import choisit le maillage dans le dossier d'après la taille de l'arbuste)
    voulu = {e["maillage_jeu"].rsplit("/", 1)[0]: e for e in man["elements"]
             if e["type"] == "InstanceGroup" and e.get("distances_de_disparition_cm")}
    mal = []
    bilan["niveau"]["composants_a_disparition_reglee"] = 0
    for o in hism:
        chemin = o["Properties"]["StaticMesh"]["ObjectPath"].split(".")[0]
        if chemin.rsplit("/", 1)[0] in voulu:
            bilan["niveau"]["composants_a_disparition_reglee"] += 1
            p, d = o["Properties"], voulu[chemin.rsplit("/", 1)[0]]["distances_de_disparition_cm"]
            if [p.get("InstanceStartCullDistance"), p.get("InstanceEndCullDistance")] != d or p.get("bCastDynamicShadow", True):
                mal.append(chemin.rsplit("/", 1)[1])
    bilan["niveau"]["herbes_mal_reglees"] = mal
    if mal:
        erreurs.append(f"herbes sans distance de disparition ou avec ombre : {mal}")
    tout = {l.strip() for l in ref("list").splitlines()}
    absents = [k for k in par if "acr/Content/" + k[len("/Game/"):] + ".uasset" not in tout]
    if absents:
        erreurs.append(f"maillages d'instances absents du jeu : {absents[:3]}")

    # sol « façon jeu »
    sol = man.get("sol", {})
    bilan["sol"] = {"mode": sol.get("mode")}
    if sol.get("mode") == "jeu":
        mis = [e for e in man["elements"] if e["type"] == "MaterialInstance" and e.get("parent_du_jeu")]
        mauvais = []
        for e in mis:
            p = exporter("acr/Content/" + e["chemin_ue"][len("/Game/"):] + ".uasset")[0]["Properties"]
            tex = {t["ParameterInfo"]["Name"]: (t["ParameterValue"] or {}).get("ObjectPath", "").split(".")[0].rsplit("/", 1)[-1]
                   for t in p.get("TextureParameterValues", [])}
            sc = {t["ParameterInfo"]["Name"]: t["ParameterValue"] for t in p.get("ScalarParameterValues", [])}
            ok = (p["Parent"]["ObjectPath"].split(".")[0] == e["parent_du_jeu"] and not p.get("bHasStaticPermutationResource")
                  and all(tex.get(k) == v for k, v in e["parametres_texture"].items())
                  and all(abs(sc.get(k, 1e30) - v) <= 1e-3 * max(1.0, abs(v)) for k, v in e["parametres_scalaires"].items()))
            if not ok:
                mauvais.append(e["nom"])
        bilan["sol"]["variantes"] = len(mis)
        bilan["sol"]["variantes_non_conformes"] = mauvais[:5]
        if mauvais:
            erreurs.append(f"{len(mauvais)} variantes de sol non conformes : {mauvais[:3]}")
        # masques : même format que ceux du jeu, et contenu relu = fichier source
        jeu = resume_vt(exporter(MASQUE_DU_JEU))
        masques = [e for e in man["elements"] if e["type"] == "Texture2D" and e["import"].get("virtual_texture_streaming")]
        differents, ecarts = [], []
        for k, e in enumerate(masques):
            chemin = "acr/Content/" + e["chemin_ue"][len("/Game/"):] + ".uasset"
            jt = exporter(chemin)
            r = resume_vt(jt)
            if r != jeu:
                differents.append((e["nom"], r))
            if k % 10 == 0:                              # contenu : un masque sur dix
                ref("raw", chemin, "--out", str(trav / "brut"))
                img = lire_masque_vt(trav / "brut" / (chemin[:-len(".uasset")] + ".ubulk"), jt[0]["VTData"])
                src = np.asarray(Image.open(Path(a.paquet) / e["fichier"]).convert("RGBA"))
                ecarts.append(float(np.abs(img.astype(np.int32) - src.astype(np.int32)).mean()))
        bilan["sol"]["masques"] = len(masques)
        bilan["sol"]["format_des_masques_du_jeu"] = jeu
        bilan["sol"]["masques_de_format_different"] = [d[0] for d in differents[:5]]
        bilan["sol"]["ecart_moyen_au_fichier_source_sur_255"] = round(max(ecarts), 2) if ecarts else None
        if differents:
            erreurs.append(f"{len(differents)} masques d'un autre format que ceux du jeu, par exemple {differents[0]}")
        if ecarts and max(ecarts) > 6.0:
            erreurs.append(f"masque relu différent de sa source (écart moyen {max(ecarts):.1f} sur 255)")
        # couleurs de sommet des maillages de sol
        sols = [e for e in man["elements"] if e["type"] == "StaticMesh" and e.get("couleur_de_sommet")]
        sans = []
        for e in sols[::5]:
            s = ref("mesh-uv", "acr/Content/" + e["chemin_ue"][len("/Game/"):] + ".uasset", "--limit", "40")
            m = re.search(r"(\d+) vertices.*colours (\d+)", s)
            couleurs = set(re.findall(r"rgba (\d+),(\d+),(\d+),(\d+)", s))
            if not m or m.group(1) != m.group(2) or couleurs != {tuple(str(v) for v in e["couleur_de_sommet"])}:
                sans.append(e["nom"])
        bilan["sol"]["maillages"] = len(sols)
        bilan["sol"]["maillages_a_mauvaise_couleur_de_sommet"] = sans[:5]
        if sans:
            erreurs.append(f"maillages dont la couleur de sommet n'est pas celle prévue : {sans[:3]}")

    # variantes qui héritent tout d'une variante du jeu (factices.json, role parent_du_jeu) : asphalte, murs
    herite = {}
    for x in json.loads((KIT / "factices.json").read_text(encoding="utf-8"))["factices"]:
        if x.get("role") == "parent_du_jeu":
            for nom in x.get("pour", []):
                herite[nom] = x["objet"]
    mal_herite, vus = [], 0
    utilises = {e.get("materiau") for e in man["elements"] if e["type"] == "StaticMesh" and e.get("acteur")}
    for e in man["elements"]:
        if e["type"] == "MaterialInstance" and e["nom"] in herite and e["nom"] in utilises:
            vus += 1
            p = exporter("acr/Content/" + e["chemin_ue"][len("/Game/"):] + ".uasset")[0]["Properties"]
            if (p["Parent"]["ObjectPath"].split(".")[0] != herite[e["nom"]] or p.get("bHasStaticPermutationResource")
                    or p.get("TextureParameterValues")):
                mal_herite.append(e["nom"])
    bilan["variantes_heritees_du_jeu"] = {"controlees": vus, "non_conformes": mal_herite}
    if mal_herite:
        erreurs.append(f"variantes qui devraient hériter d'un matériau du jeu sans rien régler : {mal_herite}")
    bilan["erreurs"] = erreurs
    (KIT / "releves" / "relecture_decor.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(bilan, ensure_ascii=False, indent=1))
    print("RELECTURE CONFORME" if not erreurs else f"RELECTURE : {len(erreurs)} ERREUR(S)")
    sys.exit(1 if erreurs else 0)


if __name__ == "__main__":
    main()
