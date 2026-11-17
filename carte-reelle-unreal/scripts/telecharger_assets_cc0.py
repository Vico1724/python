#!/usr/bin/env python3
"""Retélécharge les assets libres (CC0) listés dans un CSV : Poly Haven et ambientCG.

Usage :
  python3 telecharger_assets_cc0.py --sortie paquet/cc0 [--liste assets_cc0.csv] [--res 1k|2k]
                                    [--seulement id1,id2] [--genre texture,modele,hdri]

CSV : colonnes banque,identifiant,genre,role,cartes (cartes séparées par « ; », vide = défaut).
Défaut pour une texture Poly Haven : Diffuse, nor_gl (normale OpenGL), arm (AO/rugosité/métal) ;
à défaut d'« arm » : Rough et Displacement. Pour un modèle : le glTF et ses fichiers (.bin, textures).
ambientCG : zip <res>-JPG, seules les images utiles (couleur, normale GL, rugosité, AO, hauteur) sont extraites.
Ne retélécharge pas ce qui existe déjà. Un asset en échec n'arrête pas le script : il est listé dans le bilan.
Écrit <sortie>/sources.json et <sortie>/CREDITS.md. Bibliothèque standard uniquement.
"""
import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

AGENT = "carte-reelle-unreal/1.0"
PH_API = "https://api.polyhaven.com/"
ACG_API = "https://ambientcg.com/api/v2/full_json?id=%s&include=downloadData"
CARTES_DEFAUT = ("Diffuse", "nor_gl", "arm")
CARTES_SECOURS = ("Rough", "Displacement")           # utilisées quand « arm » n'existe pas
# images ambientCG conservées (suffixe du nom de fichier)
ACG_GARDER = ("_Color", "_NormalGL", "_Roughness", "_AmbientOcclusion", "_Displacement", "_Metalness", "_Opacity")


class Echec(Exception):
    pass


def requete(url, essais=3):
    """GET avec nouvelles tentatives ; renvoie les octets."""
    derniere = None
    for i in range(essais):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):                 # inutile de réessayer
                raise Echec("introuvable (HTTP %d)" % e.code)
            derniere = e
        except Exception as e:
            derniere = e
        time.sleep(1 + 2 * i)
    raise Echec("réseau : %s" % derniere)


def lire_json(url):
    brut = requete(url)
    try:
        return json.loads(brut)
    except ValueError:
        raise Echec("réponse non JSON : %s" % brut[:60].decode("utf-8", "replace"))


def chemin_sur(dossier, rel):
    """Chemin sous dossier ; refuse toute sortie du dossier."""
    p = os.path.normpath(os.path.join(dossier, *rel.split("/")))
    if os.path.commonpath([os.path.abspath(dossier), os.path.abspath(p)]) != os.path.abspath(dossier):
        raise Echec("chemin suspect : " + rel)
    return p


def ecrire(chemin, data):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".part"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, chemin)


def prendre(url, chemin):
    """Télécharge sauf si le fichier existe déjà. Renvoie (taille, neuf)."""
    if os.path.exists(chemin) and os.path.getsize(chemin) > 0:
        return os.path.getsize(chemin), False
    data = requete(url)
    ecrire(chemin, data)
    return len(data), True


def auteurs_polyhaven(ident):
    try:
        info = lire_json(PH_API + "info/" + urllib.parse.quote(ident))
        return ", ".join(info.get("authors", {}) or {}) or None
    except Echec:
        return None


def poly_texture(ident, cartes, res, sortie):
    fichiers = lire_json(PH_API + "files/" + urllib.parse.quote(ident))
    if not isinstance(fichiers, dict) or "gltf" not in fichiers and len(fichiers) < 2:
        raise Echec("introuvable")
    voulues = list(cartes) if cartes else list(CARTES_DEFAUT)
    if not cartes and "arm" not in fichiers:
        voulues += list(CARTES_SECOURS)
    dossier = os.path.join(sortie, ident)
    pris, neufs = {}, 0
    for carte in voulues:
        par_res = (fichiers.get(carte) or {}).get(res) or {}
        fmt = "png" if "alpha" in carte.lower() and "png" in par_res else ("jpg" if "jpg" in par_res else next(iter(par_res), None))
        if not fmt:
            continue
        url = par_res[fmt]["url"]
        rel = "%s_%s_%s.%s" % (ident, carte, res, fmt)
        taille, neuf = prendre(url, os.path.join(dossier, rel))
        neufs += neuf
        pris[rel] = {"url": url, "octets": taille, "carte": carte}
    if not pris:
        raise Echec("aucune des cartes %s en %s" % ("/".join(voulues), res))
    return pris, neufs


def poly_modele(ident, res, sortie):
    fichiers = lire_json(PH_API + "files/" + urllib.parse.quote(ident))
    try:
        g = fichiers["gltf"][res]["gltf"]
    except (KeyError, TypeError):
        raise Echec("pas de glTF en %s" % res if isinstance(fichiers, dict) and "gltf" in fichiers else "introuvable")
    dossier = os.path.join(sortie, ident)
    pris, neufs = {}, 0
    liste = [(ident + ".gltf", g["url"])] + [(k, v["url"]) for k, v in (g.get("include") or {}).items()]
    for rel, url in liste:
        taille, neuf = prendre(url, chemin_sur(dossier, rel))
        neufs += neuf
        pris[rel] = {"url": url, "octets": taille}
    return pris, neufs


def poly_hdri(ident, res, sortie):
    fichiers = lire_json(PH_API + "files/" + urllib.parse.quote(ident))
    try:
        par_fmt = fichiers["hdri"][res]
    except (KeyError, TypeError):
        raise Echec("pas de HDRI en %s" % res)
    fmt = "hdr" if "hdr" in par_fmt else next(iter(par_fmt))
    url = par_fmt[fmt]["url"]
    rel = "%s_%s.%s" % (ident, res, fmt)
    taille, neuf = prendre(url, os.path.join(sortie, ident, rel))
    return {rel: {"url": url, "octets": taille}}, int(neuf)


def acg_texture(ident, res, sortie):
    dossier = os.path.join(sortie, ident)
    d = lire_json(ACG_API % urllib.parse.quote(ident))
    trouves = d.get("foundAssets") or []
    if not trouves:
        raise Echec("introuvable")
    zips = trouves[0]["downloadFolders"]["default"]["downloadFiletypeCategories"]["zip"]["downloads"]
    attribut = res.upper() + "-JPG"
    cible = next((z for z in zips if z.get("attribute") == attribut), None)
    if not cible:
        raise Echec("pas de zip %s" % attribut)
    url = cible["fullDownloadPath"]
    existants = sorted(n for n in os.listdir(dossier) if n.lower().endswith(".jpg")) if os.path.isdir(dossier) else []
    neuf = 0
    if not any("_Color" in n for n in existants):
        z = zipfile.ZipFile(io.BytesIO(requete(url)))
        for n in z.namelist():                       # images utiles seules, sans chemin
            b = os.path.basename(n)
            if b.lower().endswith(".jpg") and b.startswith(ident) and any(s in b for s in ACG_GARDER):
                ecrire(os.path.join(dossier, b), z.read(n))
        neuf = 1
        existants = sorted(n for n in os.listdir(dossier) if n.lower().endswith(".jpg"))
    if not existants:
        raise Echec("zip sans image utile")
    pris = {n: {"url": url, "octets": os.path.getsize(os.path.join(dossier, n))} for n in existants}
    return pris, neuf, (trouves[0].get("description") or "")


def traiter(ligne, res, sortie):
    banque, ident, genre = ligne["banque"], ligne["identifiant"], ligne["genre"]
    cartes = [c.strip() for c in (ligne.get("cartes") or "").split(";") if c.strip()]
    meta = {"banque": banque, "identifiant": ident, "genre": genre, "role": ligne.get("role", ""),
            "licence": "CC0 1.0", "resolution": res}
    if banque == "polyhaven":
        meta["page"] = "https://polyhaven.com/a/" + ident
        if genre == "modele":
            pris, neufs = poly_modele(ident, res, sortie)
        elif genre == "hdri":
            pris, neufs = poly_hdri(ident, res, sortie)
        else:
            pris, neufs = poly_texture(ident, cartes, res, sortie)
        meta["auteur"] = auteurs_polyhaven(ident)
    elif banque == "ambientcg":
        meta["page"] = "https://ambientcg.com/view?id=" + ident
        pris, neufs, _ = acg_texture(ident, res, sortie)
        meta["auteur"] = "ambientCG"
    else:
        raise Echec("banque inconnue : " + banque)
    meta["fichiers"] = pris
    meta["octets"] = sum(v["octets"] for v in pris.values())
    return meta, neufs


def ecrire_credits(sortie, sources):
    lignes = ["# Crédits des assets CC0", "",
              "Tous ces assets sont placés dans le domaine public (CC0 1.0) : aucun crédit n'est obligatoire, "
              "mais les sources sont conservées ici. Poly Haven (https://polyhaven.com) et ambientCG "
              "(https://ambientcg.com) ; si l'API Poly Haven est exposée à des utilisateurs, ajouter « Powered by Poly Haven ».",
              "", "| Banque | Identifiant | Genre | Auteur | Page | Rôle |", "|---|---|---|---|---|---|"]
    for ident in sorted(sources):
        s = sources[ident]
        lignes.append("| %s | %s | %s | %s | %s | %s |" % (
            s["banque"], ident, s["genre"], s.get("auteur") or "non indiqué", s["page"], s.get("role", "").replace("|", "/")))
    with open(os.path.join(sortie, "CREDITS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")


def taille_dossier(sortie):
    return sum(os.path.getsize(os.path.join(r, n)) for r, _, fs in os.walk(sortie) for n in fs)


def main():
    ap = argparse.ArgumentParser(description="Télécharge les assets CC0 (Poly Haven, ambientCG) listés dans un CSV.")
    ici = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--liste", default=os.path.join(ici, "..", "assets", "assets_cc0.csv"), help="CSV des assets")
    ap.add_argument("--sortie", required=True, help="dossier de sortie")
    ap.add_argument("--res", default="1k", choices=["1k", "2k"], help="résolution (défaut 1k)")
    ap.add_argument("--seulement", default="", help="identifiants séparés par des virgules")
    ap.add_argument("--genre", default="", help="genres séparés par des virgules : texture, modele, hdri")
    a = ap.parse_args()

    with open(a.liste, encoding="utf-8", newline="") as f:
        lignes = [r for r in csv.DictReader(f) if (r.get("identifiant") or "").strip()]
    seuls = {s.strip() for s in a.seulement.split(",") if s.strip()}
    genres = {s.strip() for s in a.genre.split(",") if s.strip()}
    lignes = [r for r in lignes if (not seuls or r["identifiant"] in seuls) and (not genres or r["genre"] in genres)]
    os.makedirs(a.sortie, exist_ok=True)
    chemin_src = os.path.join(a.sortie, "sources.json")
    try:
        with open(chemin_src, encoding="utf-8") as f:
            sources = json.load(f).get("assets", {})
    except (OSError, ValueError):
        sources = {}

    echecs, neufs_total, nouveaux = [], 0, 0

    def tache(ligne):
        try:
            return ligne, traiter(ligne, a.res, a.sortie), None
        except Exception as e:                       # un asset en échec n'arrête pas les autres
            return ligne, None, (str(e) if isinstance(e, Echec) else "%s : %s" % (type(e).__name__, e))

    with ThreadPoolExecutor(max_workers=4) as pool:
        for ligne, res, err in pool.map(tache, lignes):
            if err:
                echecs.append((ligne["identifiant"], err))
                continue
            meta, neufs = res
            sources[ligne["identifiant"]] = meta
            neufs_total += neufs
            nouveaux += 1 if neufs else 0

    with open(chemin_src, "w", encoding="utf-8") as f:
        json.dump({"agent": AGENT, "assets": sources, "echecs": dict(echecs)}, f, ensure_ascii=False, indent=1)
    ecrire_credits(a.sortie, sources)

    ok = len(lignes) - len(echecs)
    print("Assets demandés : %d, obtenus : %d (dont %d téléchargés cette fois), en échec : %d" % (len(lignes), ok, nouveaux, len(echecs)))
    print("Volume du paquet : %.1f Mo (résolution %s) dans %s" % (taille_dossier(a.sortie) / 1e6, a.res, a.sortie))
    if echecs:
        print("Échecs : " + " ; ".join("%s (%s)" % e for e in echecs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
