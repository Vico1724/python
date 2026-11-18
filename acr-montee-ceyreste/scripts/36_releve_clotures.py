"""Relevé exhaustif des murs, murets, clôtures et de ce qui borde la route (Panoramax 08/09/2025, LiDAR HD, cadastre, OSM).

Troisième passe (18/11/2026, demande « il manque les murets, clôtures et tout »). Les deux premières passes avaient lu
des bandes de 200° à 4 px/degré et noté surtout les ouvrages ; les clôtures n'étaient pas posées, et les bornes des
murs de l'approche étaient fausses de 30 à 40 m (voir docs/03_affinage_reel.md § 9).

Usage :
  python scripts/36_releve_clotures.py planches        planches de lecture : 5 bandes de 220° par planche, 6 px/degré,
                                                       graduées tous les 30° (G90 = perpendiculaire à gauche)
  python scripts/36_releve_clotures.py lidar           signatures LiDAR par mètre et par côté (data/processed/
                                                       clotures_lidar.csv) : marche du MNT (soutènement) et objet mince
                                                       surélevé (MNS - MNT, mur ou haie)
  python scripts/36_releve_clotures.py cadastre        limites des parcelles riveraines (data/processed/
                                                       clotures_cadastre.json) : par PK et par côté, recul de la limite
                                                       parcellaire au bord de chaussée
  python scripts/36_releve_clotures.py verser          relevé brut (data/reference/releve_clotures_2025.json) -> fichier
                                                       lu par la chaîne (data/reference/clotures_murets.json), calé au
                                                       mètre par le cadastre ou le LiDAR quand ils confirment
  python scripts/36_releve_clotures.py zoom ID CAP [FOV] [ELEV]   vue agrandie (contrôle d'une lecture)

Règle : une clôture n'est posée que si une photo la montre ; le cadastre sert à la placer, jamais à l'inventer.
"""
from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from acr_geo import FIG, OUT, RAW, REF  # noqa: E402

_s = importlib.util.spec_from_file_location("p26", ICI / "26_photos_rue.py")
P26 = importlib.util.module_from_spec(_s); _s.loader.exec_module(P26)

BRUT = REF / "releve_clotures_2025.json"
SORTIE = REF / "clotures_murets.json"
PLANCHES = RAW / "panoramax" / "planches_clotures"
SOURCE = ("Panoramax, Région Sud / Immergis, 08/09/2025, images 360°, licence etalab-2.0 "
          "(data/reference/photos_rue_panoramax.csv)")


# ----------------------------------------------------------------------------------------------- planches de lecture
def _images(pk_min=-200, pk_max=4000):
    L = {r["id"]: r for r in P26.charger_liste()}
    ids = [p.stem for p in P26.DOSSIER.glob("*.jpg")]
    ids = [i for i in ids if i in L and pk_min <= float(L[i]["pk_m"]) <= pk_max]
    ids.sort(key=lambda i: float(L[i]["pk_m"]))
    return L, ids


def bande(i, r, pk, x, y, champ=220.0, haut=20.0, bas=-30.0, ppd=6.0):
    from PIL import Image, ImageDraw
    Image.MAX_IMAGE_PIXELS = None
    eq = Image.open(P26.DOSSIER / f"{i}.jpg"); W, H = eq.size
    _, lat, cap = P26.projeter(pk, x, y, float(r["x_l93"]), float(r["y_l93"]))
    c = (W / 2 + (cap - float(r["azimut_deg"])) / 360 * W) % W
    x0 = int(c - champ / 360 * W / 2); x1 = int(c + champ / 360 * W / 2)
    y0 = int((0.5 - haut / 180) * H); y1 = int((0.5 - bas / 180) * H)
    if x0 < 0 or x1 > W:
        eq = Image.fromarray(np.roll(np.asarray(eq), -x0, axis=1)); x1 -= x0; x0 = 0
    w, h = int(champ * ppd), int((haut - bas) * ppd)
    b = eq.crop((x0, y0, x1, y1)).resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(b)
    for a in range(-90, 91, 30):
        u = int((a + champ / 2) * ppd)
        d.line([(u, h - 10), (u, h)], fill=(255, 255, 0), width=2)
        d.text((u + 2, h - 22), ("G" if a < 0 else "D" if a > 0 else "") + f"{abs(a)}", fill=(255, 255, 0))
    return b, lat


def planches(par_planche=5, pk_min=-200, pk_max=4000, debut=1):
    from PIL import Image, ImageDraw
    PLANCHES.mkdir(parents=True, exist_ok=True)
    pk, x, y = P26.axe()
    L, ids = _images(pk_min, pk_max)
    # images prises hors de la D3 (voie parallèle, voie latérale : plus de 6 m de l'axe) écartées
    ids = [i for i in ids if abs(P26.projeter(pk, x, y, float(L[i]["x_l93"]), float(L[i]["y_l93"]))[1]) <= 6.0]
    index = []
    for k in range(0, len(ids), par_planche):
        lot = ids[k:k + par_planche]
        bandes = [(i, *bande(i, L[i], pk, x, y)) for i in lot]
        w, h = bandes[0][1].size
        pl = Image.new("RGB", (w, len(bandes) * (h + 18)), (0, 0, 0))
        d = ImageDraw.Draw(pl)
        for q, (i, b, lat) in enumerate(bandes):
            oy = q * (h + 18)
            pl.paste(b, (0, oy + 18))
            n = k + q
            d.text((4, oy + 3), f"[{n}] PK {float(L[i]['pk_m']):.0f}  id {i[:8]}  camera a {abs(lat):.1f} m "
                   f"{'a gauche' if lat > 0 else 'a droite'} de l'axe   G <- montee au centre -> D", fill=(255, 255, 0))
            index.append({"n": n, "pk_m": float(L[i]["pk_m"]), "id": i, "planche": k // par_planche + debut,
                          "ecart_axe_m": round(lat, 1)})
        pl.save(PLANCHES / f"planche_{k // par_planche + debut:03d}.jpg", quality=82)
    fi = PLANCHES / "index.json"
    anc = [e for e in (json.loads(fi.read_text()) if fi.exists() else []) if e["planche"] < debut]
    fi.write_text(json.dumps(anc + index, indent=0), encoding="utf-8")
    print(len(index), "bandes,", (len(index) + par_planche - 1) // par_planche, "planches ->", PLANCHES)


def zoom(i, cap, fov=50.0, elev=-5.0, largeur=1400):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    L = {r["id"]: r for r in P26.charger_liste()}
    i = next(k for k in L if k.startswith(i))
    pk, x, y = P26.axe()
    _, _, cap_route = P26.projeter(pk, x, y, float(L[i]["x_l93"]), float(L[i]["y_l93"]))
    eq = np.asarray(Image.open(P26.DOSSIER / f"{i}.jpg").convert("RGB"))
    # cap relatif au sens de la montée (D90 = +90)
    im = P26.vue_plane(eq, float(L[i]["azimut_deg"]), cap_route + float(cap), fov=float(fov), largeur=largeur,
                       tangage=float(elev))
    (PLANCHES / "zooms").mkdir(parents=True, exist_ok=True)
    out = PLANCHES / "zooms" / f"{i[:8]}_{int(float(cap))}_{int(float(fov))}.jpg"
    Image.fromarray(im).save(out, quality=88)
    print(out)


# ----------------------------------------------------------------------------------------------- LiDAR
class Bord:
    """Bords de chaussée (07) et rasters LiDAR HD 0,5 m."""

    def __init__(self):
        import rasterio
        with open(OUT / "chaussee_precise.csv", encoding="utf-8") as f:
            R = list(csv.DictReader(f))
        g = lambda *k: np.array([[float(r[a]) for a in k] for r in R])  # noqa: E731
        self.pk = g("pk_m")[:, 0]
        self.A = g("x_axe", "y_axe", "z_axe")
        self.E = {"gauche": g("x_gauche", "y_gauche", "z_gauche"), "droite": g("x_droite", "y_droite", "z_droite")}
        self.mnt = rasterio.open(RAW / "mnt_lidarhd_50cm.tif")
        self.Zt = self.mnt.read(1)
        self.Zs = rasterio.open(RAW / "mns_lidarhd_50cm.tif").read(1)
        self.inv = ~self.mnt.transform

    def z(self, Z, x, y):
        c, r = self.inv * (np.asarray(x), np.asarray(y))
        r = np.clip(np.floor(r).astype(int), 0, Z.shape[0] - 1); c = np.clip(np.floor(c).astype(int), 0, Z.shape[1] - 1)
        return Z[r, c].astype(float)

    def normale(self, cote):
        n = self.E[cote][:, :2] - self.A[:, :2]
        return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)

    def point(self, pk, cote, recul):
        """Point L93 (x, y) à `recul` m au-delà du bord de chaussée, au PK donné (interpolé)."""
        pk = np.atleast_1d(np.asarray(pk, float)); recul = np.broadcast_to(np.asarray(recul, float), pk.shape)
        E = np.column_stack([np.interp(pk, self.pk, self.E[cote][:, k]) for k in range(3)])
        n = self.normale(cote)
        nn = np.column_stack([np.interp(pk, self.pk, n[:, 0]), np.interp(pk, self.pk, n[:, 1])])
        nn /= np.maximum(np.linalg.norm(nn, axis=1, keepdims=True), 1e-9)
        return E[:, :2] + nn * recul[:, None], E[:, 2]


def lidar():
    B = Bord()
    off = np.arange(0.0, 12.01, 0.25)
    lignes = []
    for cote in ("gauche", "droite"):
        n = B.normale(cote)
        E = B.E[cote]
        X = E[:, 0:1] + n[:, 0:1] * off[None]; Y = E[:, 1:2] + n[:, 1:2] * off[None]
        zt = B.z(B.Zt, X, Y) - E[:, 2:3]
        zs = B.z(B.Zs, X, Y) - B.z(B.Zt, X, Y)
        for k in range(len(B.pk)):
            if abs(B.pk[k] - round(B.pk[k])) > 1e-6:
                continue
            # marche du MNT : plus forte montée (ou descente) sur 1 m
            d = zt[k, 4:] - zt[k, :-4]
            j = int(np.argmax(np.abs(d)))
            marche, recul_m = float(d[j]), float(off[j] + 0.5)
            # objet mince surélevé : MNS - MNT de 0,4 à 3 m sur 1,25 m au plus, bas (< 0,3 m) de part et d'autre
            mince, recul_o = 0.0, None
            for jj in range(2, len(off) - 6):
                h = zs[k, jj]
                if 0.4 <= h <= 3.0 and zs[k, jj - 2] < 0.3 and min(zs[k, jj + 3:jj + 7]) < 0.3:
                    mince, recul_o = float(h), float(off[jj]); break
            lignes.append({"pk_m": int(round(B.pk[k])), "cote": cote, "marche_mnt_m": round(marche, 2),
                           "recul_marche_m": recul_m, "objet_mince_h_m": round(mince, 2),
                           "recul_objet_m": recul_o if recul_o is None else round(recul_o, 2),
                           "mns_mnt_0_3m": round(float(np.median(zs[k, :13])), 2)})
    with open(OUT / "clotures_lidar.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(lignes[0])); w.writeheader(); w.writerows(lignes)
    print(len(lignes), "lignes ->", OUT / "clotures_lidar.csv")


# ----------------------------------------------------------------------------------------------- cadastre
def _parcelles():
    import shapely
    from pyproj import Transformer
    tr = Transformer.from_crs(4326, 2154, always_xy=True)
    d = json.loads(gzip.open(RAW / "cadastre" / "parcelles.json.gz").read())
    geoms = []
    for f in d["features"]:
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for p in polys:
            ring = np.array(p[0])
            xx, yy = tr.transform(ring[:, 0], ring[:, 1])
            geoms.append((f["properties"].get("id"), shapely.polygons(np.column_stack([xx, yy]))))
    return geoms


def cadastre(pas=1.0, portee=15.0):
    """Pour chaque PK (pas 1 m) et chaque côté : recul au bord de chaussée de la première limite parcellaire rencontrée
    en allant vers l'extérieur (rayon perpendiculaire), jusqu'à `portee` m. Écrit aussi les segments de limite en L93."""
    import shapely
    B = Bord()
    geoms = _parcelles()
    zone = shapely.box(B.A[:, 0].min() - 30, B.A[:, 1].min() - 30, B.A[:, 0].max() + 30, B.A[:, 1].max() + 30)
    proches = [(i, g) for i, g in geoms if g.intersects(zone)]
    bords = shapely.union_all([shapely.boundary(g) for _, g in proches])
    res = {"source": "cadastre Etalab (cadastre.data.gouv.fr, PCI vecteur, millésime « latest » téléchargé le "
                     "18/11/2026), parcelles de la commune 13023", "pas_m": pas, "portee_m": portee,
           "nb_parcelles_proches": len(proches), "gauche": [], "droite": []}
    pks = np.arange(np.ceil(B.pk[0]), np.floor(B.pk[-1]) + 0.01, pas)
    for cote in ("gauche", "droite"):
        P0, _ = B.point(pks, cote, -0.5)
        P1, _ = B.point(pks, cote, portee)
        for p, a, b in zip(pks, P0, P1):
            ray = shapely.linestrings([a, b])
            it = shapely.intersection(ray, bords)
            if it.is_empty:
                res[cote].append(None); continue
            pts = shapely.get_coordinates(it)
            dd = np.hypot(pts[:, 0] - a[0], pts[:, 1] - a[1]) - 0.5
            res[cote].append(round(float(dd.min()), 2))
    res["pk0"] = float(pks[0])
    (OUT / "clotures_cadastre.json").write_text(json.dumps(res), encoding="utf-8")
    for cote in ("gauche", "droite"):
        v = np.array([np.nan if q is None else q for q in res[cote]])
        print(cote, f"limite trouvée sur {np.isfinite(v).mean() * 100:.0f} % des PK ; recul médian {np.nanmedian(v):.1f} m")


# ----------------------------------------------------------------------------------------------- versement
def _cad():
    c = json.loads((OUT / "clotures_cadastre.json").read_text(encoding="utf-8"))
    return c


def verser():
    brut = json.loads(BRUT.read_text(encoding="utf-8"))
    B = Bord()
    cad = _cad()
    lid = {}
    with open(OUT / "clotures_lidar.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            lid[(int(r["pk_m"]), r["cote"])] = r
    out, bilan = [], {"cale_cadastre": 0, "cale_lidar": 0, "photo": 0}
    for e in brut["elements"]:
        a, b = float(e["pk_debut_m"]), float(e["pk_fin_m"])
        pks = np.arange(a, b + 0.01, 1.0) if b - a >= 1 else np.array([a, b])
        cote = e["cote"]
        recul = float(e.get("recul_m", 0.5))
        calage = "photo (±5 m en long, ±1 m en travers)"
        recul_v = np.full(len(pks), recul)
        pl = e.get("placement", "photo")
        ponctuel = e["type"] in ("pilier", "boites_aux_lettres") or b - a < 4
        # Essai automatique (élément photo de 4 m et plus) : limite cadastrale pour ce qui ferme une propriété, marche
        # du MNT pour un mur ou une restanque. N'est retenu que si la source concorde avec la lecture photo (± tol).
        essais = [] if pl == "trace_releve" else [pl] if pl != "photo" else ([] if ponctuel else (["lidar", "cadastre"] if e["type"] == "pierre_seche"
                                                                   else ["cadastre"]))
        tol_def = 2.5 if pl == "cadastre" else 1.5
        for src in essais:
            tol = float(e.get("tolerance_cadastre_m", tol_def))
            if src == "cadastre":
                k = np.clip(np.round(pks - cad["pk0"]).astype(int), 0, len(cad[cote]) - 1)
                v = np.array([np.nan if cad[cote][q] is None else cad[cote][q] for q in k])
                ok = np.isfinite(v) & (np.abs(v - recul) < tol)
                if ok.mean() >= 0.6:
                    idx = np.arange(len(v))
                    vv = np.interp(idx, idx[ok], v[ok])            # trous comblés, lissage sur 5 m
                    recul_v = np.convolve(np.pad(vv, 2, mode="edge"), np.ones(5) / 5, mode="valid")
                    calage = "au mètre (limite cadastrale, existence vue sur photo)"
                    bilan["cale_cadastre"] += 1
                    break
                calage = f"photo (cadastre non concordant : {ok.mean() * 100:.0f} % des PK)"
            else:
                rr = [lid.get((int(round(p)), cote)) for p in pks]
                v = np.array([float(r["recul_marche_m"]) if r and abs(float(r["marche_mnt_m"])) >= max(0.5, 0.5 * float(e["hauteur_m"]))
                              else np.nan for r in rr])
                ok = np.isfinite(v) & (np.abs(v - recul) < tol)
                if ok.mean() >= 0.5:
                    idx = np.arange(len(v))
                    vv = np.interp(idx, idx[ok], v[ok])
                    recul_v = np.convolve(np.pad(vv, 2, mode="edge"), np.ones(5) / 5, mode="valid") - 0.25
                    calage = "au mètre (marche du MNT LiDAR HD, existence vue sur photo)"
                    bilan["cale_lidar"] += 1
                    break
        recul_v = np.maximum(recul_v, 0.25)            # jamais sur la chaussée (limite cadastrale dans l'enrobé)
        xy, zb = B.point(pks, cote, recul_v)
        if pl == "trace_releve":
            # pied relevé ailleurs (carrefour du départ : marche du MNT derrière une voie latérale, que le recul au bord
            # de la chaussée de la spéciale ne sait pas décrire ; data/reference/depart_carrefour.json, clé « mur »)
            rr = json.loads((REF / e["trace_releve"]).read_text(encoding="utf-8"))
            xy = np.asarray(rr["mur"]["pied"], float) + np.asarray(rr["origine_l93"], float)
            dE = np.hypot(*(xy[:, None, :] - B.E[cote][None, :, :2]).transpose(2, 0, 1)).min(1)
            recul_v = dE
            calage = "au mètre (pied relevé sur la marche du MNT LiDAR HD, " + e["trace_releve"] + ", existence vue sur photo)"
            bilan["cale_lidar"] += 1
        if not calage.startswith("au mètre"):
            bilan["photo"] += 1
        s = dict(e)
        s.update({"calage": calage, "trace_l93": np.round(xy, 2).tolist(), "recul_applique_m":
                  [round(float(np.min(recul_v)), 2), round(float(np.max(recul_v)), 2)],
                  "longueur_m": round(float(np.sum(np.hypot(*np.diff(xy, axis=0).T))) if len(xy) > 1 else 0.0, 1)})
        out.append(s)
    ponct = []
    for e in brut.get("ponctuels", []):
        cote = e["cote"]
        xy, zb = B.point([float(e["pk_m"])], cote, float(e.get("recul_m", 0.8)))
        s = dict(e)
        s.update({"calage": "photo (±5 m en long, ±1 m en travers)", "position_l93": np.round(xy[0], 2).tolist()})
        ponct.append(s)
    corriger_ouvrages(brut.get("corrections_ouvrages", []))
    registre = faire_registre(out)
    doc = {"note": "Murs, murets, clôtures, portails, haies du bord de la montée (troisième passe, 18/11/2026). Écrit "
                   "par scripts/36_releve_clotures.py verser depuis data/reference/releve_clotures_2025.json ; lu par "
                   "scripts/37_clotures.py (géométrie). trace_l93 : polyligne au pied, côté route.",
           "source_images": SOURCE, "elements": out, "ponctuels": ponct, "bilan_calage": bilan}
    SORTIE.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "clotures_registre.json").write_text(json.dumps(registre, ensure_ascii=False, indent=0), encoding="utf-8")
    print(SORTIE, len(out), "éléments", len(ponct), "ponctuels", bilan)
    print("registre :", registre["bilan"])


def corriger_ouvrages(corr):
    """Corrections du relevé des deux premières passes (bornes fausses, murets remplacés par un élément composé), dans
    le relevé brut (releve_panoramax_2025.json, pour que 29 les garde) et dans ouvrages_parapets.json. Idempotent."""
    fb, fo = REF / "releve_panoramax_2025.json", REF / "ouvrages_parapets.json"
    brut, ouv = json.loads(fb.read_text(encoding="utf-8")), json.loads(fo.read_text(encoding="utf-8"))
    for c in corr:
        a, b = c["pk_photo"]
        # relevé brut : entrée « parapet » du même côté, bornes photo égales
        keep = []
        for e in brut["releve"]:
            if e.get("categorie") == "parapet" and e.get("cote") == c["cote"] and [e["pk_debut_m"], e["pk_fin_m"]] == [a, b]:
                if c["action"] == "bornes":
                    e["pk_debut_m"], e["pk_fin_m"] = c["pk"]; e["pk_photo_corrige"] = c["raison"]
                    c2 = dict(c); c2["pk_photo"] = c["pk"]
                    keep.append(e)
                continue
            keep.append(e)
        brut["releve"] = keep
        # fichier lu par la chaîne : entrée dont pk_photo_m (ou les bornes) recouvre [a, b] du même côté
        garde = []
        for e in ouv["parapets_hors_tablier"]:
            p = e.get(c["cote"])
            if p and p.get("type", "aucun") != "aucun":
                ph = p.get("pk_photo_m", [e["pk_debut_m"], e["pk_fin_m"]])
                if [float(ph[0]), float(ph[1])] == [float(a), float(b)]:
                    if c["action"] == "retirer":
                        continue
                    e["pk_debut_m"], e["pk_fin_m"] = c["pk"]; p["pk_photo_m"] = c["pk"]
                    note = f" ; bornes corrigées le 18/11/2026 (troisième passe) : {c['raison']}"
                    if note not in p.get("statut", ""):                  # idempotent (relances de verser)
                        p["statut"] = f"{p.get('statut', '')}{note}"
            garde.append(e)
        ouv["parapets_hors_tablier"] = garde
        if c["action"] == "bornes":                      # rejouable : la correction est maintenant la référence
            c["pk_photo"] = c["pk"]
    fb.write_text(json.dumps(brut, ensure_ascii=False, indent=1), encoding="utf-8")
    fo.write_text(json.dumps(ouv, ensure_ascii=False, indent=1), encoding="utf-8")
    fr = BRUT
    d = json.loads(fr.read_text(encoding="utf-8")); d["corrections_ouvrages"] = corr
    fr.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")


def faire_registre(elements, pas=50):
    """Un état par tronçon de 50 m et par côté : ce qui borde la route (relevés des trois passes) et les images lues."""
    ix = json.loads((PLANCHES / "index.json").read_text(encoding="utf-8"))
    ouv = json.loads((REF / "ouvrages_parapets.json").read_text(encoding="utf-8"))["parapets_hors_tablier"]
    gl = json.loads((REF / "glissieres.json").read_text(encoding="utf-8"))["troncons"]
    par = json.loads((REF / "parois_rocheuses.json").read_text(encoding="utf-8"))["parois"]
    lin = []
    for e in elements:
        lin.append((e["pk_debut_m"], e["pk_fin_m"], e["cote"], e["type"]))
    for e in ouv:
        for c in ("gauche", "droite"):
            if e.get(c, {}).get("type", "aucun") != "aucun":
                lin.append((e["pk_debut_m"], e["pk_fin_m"], c, "mur/parapet (passes 1-2)" if e[c].get("rendu") != "roche"
                            else "paroi"))
    for g in gl:
        lin.append((g["pk_debut_m"], g["pk_fin_m"], g.get("cote", "gauche"), "glissière"))
    for p in par:
        lin.append((p.get("pk_debut_m", 0), p.get("pk_fin_m", 0), p.get("cote", ""), "talus rocheux"))
    out, bilan = [], {"troncons": 0, "examines": 0, "sans_image": 0}
    for a in range(-150, 3750, pas):
        b = a + pas
        imgs = [x["id"][:8] for x in ix if a - 8 <= x["pk_m"] < b + 8]
        for c in ("gauche", "droite"):
            t = sorted({ty for (p0, p1, cc, ty) in lin if cc == c and p0 < b and p1 > a})
            etat = ", ".join(t) if t else "rien (talus nu, fossé ou végétation)"
            out.append({"pk": [a, b], "cote": c, "etat": etat, "images": imgs})
            bilan["troncons"] += 1
            bilan["examines" if imgs else "sans_image"] += 1
    return {"note": "registre de la troisième passe (18/11/2026) : chaque tronçon de 50 m, chaque côté, examiné sur "
                    "les planches de 36 ; « rien » = examiné, sans mur ni clôture au bord", "bilan": bilan, "troncons": out}


if __name__ == "__main__":
    a = sys.argv[1:] or ["planches"]
    if a[0] == "planches":
        planches(pk_min=float(a[1]) if len(a) > 1 else -200, pk_max=float(a[2]) if len(a) > 2 else 4000,
                 debut=int(a[3]) if len(a) > 3 else 1)
    elif a[0] == "lidar":
        lidar()
    elif a[0] == "cadastre":
        cadastre()
    elif a[0] == "verser":
        verser()
    elif a[0] == "zoom":
        zoom(*a[1:])
