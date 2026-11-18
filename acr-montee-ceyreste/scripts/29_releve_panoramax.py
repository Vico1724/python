"""Relevé du bord de route d'après l'imagerie Panoramax (08/09/2025), recalé sur le LiDAR HD, versé dans les fichiers
de relevé que lit la chaîne (11, 12, 15b, 16, 09).

Entrée : data/reference/releve_panoramax_2025.json  (relevé brut, objet par objet : PK et côté lus sur les planches de
         scripts/26_photos_rue.py, identifiants des images, description, confiance). Écrit à la main, image par image.
Recalage : pour chaque objet en long, la signature LiDAR est cherchée le long du bord de chaussée, dans les bornes lues
         sur les photos élargies de 15 m :
           - mur, muret, parapet, glissière (h <= 1,5 m) : MNS 0,5 m au-dessus du bord de chaussée de 0,3 m au moins et
             de h + 0,6 m au plus, entre 0,2 et 1,4 m au-delà du bord ; OU terrain (MNT) qui monte d'au moins 0,6 x h
             à 1,5 m du bord (mur de soutènement d'un talus) ;
           - paroi, talus rocheux, grand mur (h > 1,5 m) : MNT qui monte d'au moins 1 m entre 0,5 et 3 m du bord.
         Si une suite continue de signature (trous de 3 m au plus) couvre au moins la moitié de la longueur lue, ses
         bornes remplacent celles des photos : « positionné au mètre (LiDAR) ». Sinon les bornes des photos restent :
         « approximatif (photo, ±10 m) ». Les objets ponctuels restent approximatifs (PK lu sur la photo, ±5 à 10 m).
Sorties : data/reference/glissieres.json (troncons), ouvrages_parapets.json (ouvrages, parapets_hors_tablier),
         parois_rocheuses.json (parois), mobilier_bord_de_route.json (objets, non_poses),
         data/processed/releve_panoramax_bilan.json, figures/affinage/releve_panoramax.png
"""
from __future__ import annotations

import copy
import csv
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parent))
from acr_geo import FIG, OUT, RAW, REF  # noqa: E402

BRUT = REF / "releve_panoramax_2025.json"
DATE = "18/11/2026"
SOURCE = "Panoramax, Région Sud / Immergis, 08/09/2025, images 360°, licence etalab-2.0 (data/reference/photos_rue_panoramax.csv)"


class Bord:
    def __init__(self):
        with open(OUT / "chaussee_precise.csv", encoding="utf-8") as f:
            R = list(csv.DictReader(f))
        g = lambda *k: np.array([[float(r[a]) for a in k] for r in R])  # noqa: E731
        self.pk = g("pk_m")[:, 0]
        self.A = g("x_axe", "y_axe", "z_axe")
        self.E = {"gauche": g("x_gauche", "y_gauche", "z_gauche"), "droite": g("x_droite", "y_droite", "z_droite")}
        self.mnt = rasterio.open(RAW / "mnt_lidarhd_50cm.tif")
        self.mns = rasterio.open(RAW / "mns_lidarhd_50cm.tif")
        self.Zt, self.Zs = self.mnt.read(1), self.mns.read(1)
        self.inv = ~self.mnt.transform

    def z(self, Z, x, y):
        c, r = self.inv * (np.asarray(x), np.asarray(y))
        r = np.clip(np.floor(r).astype(int), 0, Z.shape[0] - 1); c = np.clip(np.floor(c).astype(int), 0, Z.shape[1] - 1)
        return Z[r, c].astype(float)

    def profil(self, a, b, cote, offsets):
        sel = (self.pk >= a) & (self.pk <= b)
        P, E, A = self.pk[sel], self.E[cote][sel], self.A[sel]
        n = E[:, :2] - A[:, :2]; n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        X = E[:, 0:1] + n[:, 0:1] * offsets[None]; Y = E[:, 1:2] + n[:, 1:2] * offsets[None]
        return P, E[:, 2], self.z(self.Zt, X, Y), self.z(self.Zs, X, Y)


def suites(m, trou=3):
    out, k = [], 0
    while k < len(m):
        if m[k]:
            j, vide = k, 0
            while j + 1 < len(m) and (m[j + 1] or vide < trou):
                vide = 0 if m[j + 1] else vide + 1
                j += 1
            while not m[j]:
                j -= 1
            out.append((k, j)); k = j + 1
        else:
            k += 1
    return out


def recaler(bord, e):
    a, b, cote, h = float(e["pk_debut_m"]), float(e["pk_fin_m"]), e["cote"], e.get("hauteur_m")
    if isinstance(h, list):
        h = max(h)
    off = np.arange(0.2, 3.01, 0.25)
    P, ze, T, S = bord.profil(a - 15, b + 15, cote, off)
    if len(P) < 5:
        return None
    dT, dS = T - ze[:, None], S - ze[:, None]
    if h is not None and h <= 1.5 and e["categorie"] != "paroi":
        proche = off <= 2.0
        haut = (dS[:, proche] > 0.3) & (dS[:, proche] < h + 0.6)
        # au-dessus du sol (MNS > MNT), ou mur pris dans le MNT : bosse de 0,3 m au moins avec une chute derrière
        bosse = np.zeros_like(haut)
        bosse[:, :-4] = (T[:, proche][:, :-4] - T[:, proche][:, 4:]) > 0.3
        objet = (haut & ((S[:, proche] - T[:, proche] > 0.2) | bosse)).any(1)
        talus = dT[:, np.argmin(abs(off - 1.5))] > 0.6 * h
        sig = objet | talus
    else:
        loin = (off >= 0.5) & (off <= 3.0)
        sig = (dT[:, loin].max(1) > 1.0)
    best = None
    for i, j in suites(sig):
        recouvre = min(P[j], b) - max(P[i], a)
        if recouvre > 0 and (best is None or recouvre > best[2]):
            best = (P[i], P[j], recouvre)
    part = float(sig[(P >= a) & (P <= b)].mean()) if ((P >= a) & (P <= b)).any() else 0.0
    if best and best[2] >= 0.5 * (b - a):
        # une suite qui touche le bord de la fenêtre de recherche ne dit rien de la borne de ce côté : on garde la photo
        best = (a if best[0] <= P[0] + 0.5 else best[0], b if best[1] >= P[-1] - 0.5 else best[1], best[2])
        # décalage du pied d'une paroi : premier point où le terrain monte de 0,5 m
        dec = None
        if e["categorie"] == "paroi":
            m = (P >= best[0]) & (P <= best[1])
            k = np.argmax(dT[m] > 0.5, axis=1)
            dec = float(np.median(off[k])) if m.any() else None
        return {"pk": (float(best[0]), float(best[1])), "part_signature": round(part, 2), "decalage_m": dec,
                "bornes_lidar": [best[0] != a, best[1] != b]}
    return {"pk": None, "part_signature": round(part, 2), "decalage_m": None}


def main():
    brut = json.loads(BRUT.read_text(encoding="utf-8"))
    ids = {}
    with open(REF / "photos_rue_panoramax.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ids[r["id"]] = r
    bord = Bord()
    bilan = {"date": DATE, "objets": [], "compte": {}}
    gl, par, ouv, paro, obj, nonp = [], [], [], [], [], []
    for e in brut["releve"]:
        for i in e["images"]:
            assert i in ids, f"image inconnue {i}"
        imgs = e["images"]
        src = f"{SOURCE} ; images {', '.join(i[:8] for i in imgs)}"
        conf = e.get("confiance", "moyenne")
        if e["categorie"] == "ponctuel":
            pos = "approximatif (photo, PK ±10 m)"
            rec = None
        else:
            rec = recaler(bord, e) if e["type"] != "aucun" else None
            pos = ("positionné au mètre (LiDAR HD : signature de " + ("talus" if e["categorie"] == "paroi" else "mur ou glissière")
                   + " le long du bord)") if rec and rec["pk"] else "approximatif (photo, PK ±10 m)"
        a, b = (rec["pk"] if rec and rec["pk"] else (e.get("pk_debut_m"), e.get("pk_fin_m")))
        ligne = {"categorie": e["categorie"], "type": e["type"], "cote": e["cote"],
                 "pk_photo": [e.get("pk_debut_m"), e.get("pk_fin_m")] if "pk_debut_m" in e else e["pk_m"],
                 "pk_retenu": [a, b] if "pk_debut_m" in e else e["pk_m"], "positionnement": pos,
                 "part_signature_lidar": rec["part_signature"] if rec else None, "description": e["description"]}
        bilan["objets"].append(ligne)
        k = (e["categorie"], pos.split(" ")[0])
        bilan["compte"][f"{k[0]} | {k[1]}"] = bilan["compte"].get(f"{k[0]} | {k[1]}", 0) + 1
        com = {"source": src, "images": imgs, "statut": f"vu sur Panoramax (images du 08/09/2025, relevé du {DATE})", "positionnement": pos,
               "confiance": conf, "description": e["description"]}
        if e["categorie"] != "ponctuel":
            com["pk_photo_m"] = [e["pk_debut_m"], e["pk_fin_m"]]
        if e["categorie"] == "glissiere":
            gl.append({"pk_debut_m": round(a, 1), "pk_fin_m": round(b, 1), "cote": e["cote"], "detail": "glissière simple",
                       "confiance_bornes": "±1 m" if rec and rec["pk"] else "±10 m", **com})
        elif e["categorie"] in ("parapet", "ouvrage"):
            if e["type"] == "aucun":
                continue
            p = {"type": e["type"], "hauteur_m": e["hauteur_m"], "epaisseur_m": 0.45 if e["type"] == "pierre" else 0.3,
                 **com}
            autre = "droite" if e["cote"] == "gauche" else "gauche"
            par.append({"pk_debut_m": round(a, 1), "pk_fin_m": round(b, 1), "route": "D3", e["cote"]: p,
                        autre: {"type": "aucun", "statut": "non relevé de ce côté dans cette entrée"}})
        elif e["categorie"] == "paroi":
            h = e["hauteur_m"]
            paro.append({"pk_debut_m": round(a, 1), "pk_fin_m": round(b, 1), "cote": e["cote"],
                         "decalage_m": round(rec["decalage_m"], 2) if rec and rec.get("decalage_m") else 1.0,
                         "hauteur_m": h, "genre": e["type"], "raide": e["type"] == "lite", "couleur": e.get("couleur", ""),
                         **com})
        else:
            if e.get("non_pose"):
                nonp.append(f"{e['description']} (PK ≈ {e['pk_m']}, {e['cote']}) : {e['non_pose']} ; images "
                            f"{', '.join(i[:8] for i in imgs)}")
                continue
            obj.append({"type": e["type"], "pk_m": e["pk_m"], "cote": e["cote"],
                        "decalage_m": {"balise_virage": 1.3, "borne_kilometrique": 0.6, "poteau_bois": 1.5}.get(e["type"], 0.9),
                        **com, **({"substitut": e["substitut"]} if e.get("substitut") else {})})
    # --- écriture dans les fichiers de la chaîne
    def maj(nom, fn):
        f = REF / nom
        d = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        fn(d)
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def f_gl(d):
        d["note"] = ("Glissières de la montée, relevées le " + DATE + " sur Panoramax (scripts/29_releve_panoramax.py, relevé brut "
                     "data/reference/releve_panoramax_2025.json) et recalées sur le LiDAR HD quand il les voit. Géométrie et noms "
                     "du jeu repris du Grand Caunet (supposés).")
        d["troncons"] = gl

    def f_par(d):
        d["note"] = ("Parapets, murs et murets de bord de route de la montée (D3), relevés le " + DATE + " sur Panoramax "
                     "(scripts/29_releve_panoramax.py) et recalés sur le LiDAR HD quand il les voit. Les clôtures, garde-corps "
                     "métalliques et bandes peintes ne sont pas rendus (voir la description de chaque entrée).")
        d["ouvrages"] = [{"pk_centre_m": 2016.0, "route": "D3", "bdtopo_pk": "2009-2023",
                          "gauche": {"type": "beton", "hauteur_m": 0.55, "epaisseur_m": 0.3, "statut": f"vu sur Panoramax (images du 08/09/2025, relevé du {DATE})",
                                     "source": f"{SOURCE} ; images b6721f3d, b9a4f318", "confiance": "moyenne",
                                     "note": "tête basse en béton, tags (non reproduits), extrémité peinte en blanc"},
                          "droite": {"type": "beton", "hauteur_m": 0.55, "epaisseur_m": 0.3, "statut": f"vu sur Panoramax (images du 08/09/2025, relevé du {DATE})",
                                     "source": f"{SOURCE} ; images b6721f3d, b9a4f318", "confiance": "moyenne",
                                     "note": "tête basse en béton, extrémité peinte en blanc"}}]
        d["parapets_hors_tablier"] = [p for p in par if not (2000 <= p["pk_debut_m"] <= 2030)]
        d.pop("a_relever", None)

    def f_paro(d):
        d.setdefault("genres", {"lite": "roche en place, front continu et raide : maillage de roche (16_paquet_unreal.py)",
                                "eboulis": "rocaille : talus incliné de pierres, de roche brisée et de terre ; pas de maillage, "
                                           "sol peint en pierraille (15b) et pierres semées (16)"})
        d["note"] = ("Parois et talus rocheux du bord de la montée, relevés le " + DATE + " sur Panoramax (scripts/29_releve_panoramax.py) "
                     "et recalés sur le LiDAR HD (montée du MNT d'au moins 1 m entre 0,5 et 3 m du bord).")
        d["parois"] = paro

    def f_mob(d):
        gc = MOBILIER_TYPES
        d["note"] = ("Mobilier de bord de route de la montée, relevé le " + DATE + " sur Panoramax (scripts/29_releve_panoramax.py). "
                     "Types et maillages du jeu repris du Grand Caunet (vérifiés là-bas). PK approximatifs (±10 m). Les objets "
                     "sans maillage du jeu sont listés dans non_poses ; les substituts sont signalés par « substitut ».")
        d["types"] = gc
        d.setdefault("lignes_electriques", [])
        d["objets"] = obj
        d["non_poses"] = nonp
    maj("glissieres.json", f_gl)
    maj("ouvrages_parapets.json", f_par)
    maj("parois_rocheuses.json", f_paro)
    maj("mobilier_bord_de_route.json", f_mob)
    (OUT / "releve_panoramax_bilan.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(bilan["compte"], ensure_ascii=False, indent=1))
    figure(bilan)


# Types du jeu repris du Grand Caunet (acr-grand-caunet/data/reference/mobilier_bord_de_route.json, lecture seule),
# limités à ceux posés ici. Noms vérifiés là-bas dans le catalogue du jeu.
MOBILIER_TYPES = json.loads((REF / "mobilier_types_du_jeu.json").read_text(encoding="utf-8")) \
    if (REF / "mobilier_types_du_jeu.json").exists() else {}


def figure(bilan):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    col = {"glissiere": "#7f8c8d", "parapet": "#a0522d", "ouvrage": "#2c3e50", "paroi": "#d4ac0d", "ponctuel": "#c0392b"}
    fig, ax = plt.subplots(figsize=(16, 4.8))
    for o in bilan["objets"]:
        y = 1 if o["cote"] == "gauche" else -1
        c = col[o["categorie"]]
        dy = {"glissiere": 0.15, "parapet": 0.3, "ouvrage": 0.3, "paroi": 0.45, "ponctuel": 0.6}[o["categorie"]] * y
        if isinstance(o["pk_retenu"], list):
            a, b = o["pk_retenu"]
            ls = "-" if o["positionnement"].startswith("positionné") else ":"
            ax.plot([a, b], [dy, dy], color=c, lw=5, ls=ls, solid_capstyle="butt")
            if o["pk_photo"] != o["pk_retenu"]:
                ax.plot(o["pk_photo"], [dy + 0.06 * y] * 2, color=c, lw=1, alpha=0.6)
        else:
            ax.plot(o["pk_retenu"], dy, "v" if y < 0 else "^", color=c, ms=7)
    for k, c in col.items():
        ax.plot([], [], color=c, lw=5, label=k)
    ax.plot([], [], color="k", lw=5, label="trait plein : bornes au mètre (LiDAR)")
    ax.plot([], [], color="k", lw=5, ls=":", label="pointillé : bornes des photos (±10 m)")
    ax.axhline(0, color="k", lw=0.8); ax.axvline(0, color="g", lw=1); ax.axvline(3000, color="r", lw=1)
    ax.set_yticks([0.4, -0.4]); ax.set_yticklabels(["gauche", "droite"]); ax.set_xlim(-160, 3780)
    ax.set_xlabel("PK (m) ; départ en vert, arrivée estimée en rouge"); ax.legend(ncol=4, fontsize=8, loc="upper center",
                                                                              bbox_to_anchor=(0.5, 1.25))
    ax.set_title("Relevé du bord de route (Panoramax 08/09/2025, recalé LiDAR HD)", pad=34)
    fig.tight_layout(); (FIG / "affinage").mkdir(exist_ok=True)
    fig.savefig(FIG / "affinage" / "releve_panoramax.png", dpi=110); plt.close(fig)


if __name__ == "__main__":
    main()
