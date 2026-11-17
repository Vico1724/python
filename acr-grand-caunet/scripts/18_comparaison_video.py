"""Compare l'enchaînement des virages du tracé (data/processed/chaussee_precise.csv) à ce que montrent les vidéos
embarquées : sens, ordre et ampleur de chaque changement de direction. Ne modifie rien.

Méthode. Quand la voiture tourne, tout le paysage lointain glisse dans l'image du côté opposé. Le glissement
horizontal d'une image à la suivante, mesuré par corrélation de phase sur une bande située au-dessus du capot, est
donc proportionnel à la vitesse de lacet. Sa somme donne le cap de la voiture, à un facteur d'échelle près (il dépend
de l'objectif) et à un signe près.
  1. le cap vu par la vidéo et le cap du tracé sont découpés en changements de direction successifs (un nouveau
     segment commence quand le cap repart dans l'autre sens de plus de SEUIL_DEG) ;
  2. les deux suites de changements sont alignées l'une sur l'autre (programmation dynamique), sans supposer la
     vitesse de la voiture ; l'échelle de la vidéo est celle qui donne le meilleur alignement ;
  3. pour chaque virage du tracé, on lit l'angle que la vidéo lui donne.
Ce que la méthode vérifie : l'ordre et le sens des virages, et leur ampleur angulaire. Ce qu'elle ne vérifie pas :
les rayons (il faudrait la vitesse), les largeurs, les dévers. Limites : une glissade ou un contre-braquage tournent
la caméra sans que la route tourne ; l'échelle est supposée constante sur toute la vidéo.

Usage : python scripts/18_comparaison_video.py [dossier des vidéos]   (défaut : le dossier Projet_grand_caunet)
Sorties : data/processed/comparaison_video.json ; les mesures de lacet sont gardées dans data/raw/video_lacet/.
"""
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy.signal import savgol_filter

RACINE = Path(__file__).resolve().parents[1]
SEUIL_DEG = 12.0
LARGEUR = 384


def lacet_video(chemin, cache):
    """Glissement horizontal (pixels par image, à LARGEUR px de large) et cadence de la vidéo."""
    f = cache / (chemin.stem[:60].replace(" ", "_") + ".npz")
    if f.exists():
        z = np.load(f)
        return z["dx"], float(z["fps"])
    c = cv2.VideoCapture(str(chemin))
    fps = c.get(cv2.CAP_PROP_FPS)
    h = int(round(LARGEUR * c.get(cv2.CAP_PROP_FRAME_HEIGHT) / c.get(cv2.CAP_PROP_FRAME_WIDTH)))
    y0, y1 = int(0.18 * h), int(0.52 * h)                       # au-dessus du capot, sous le haut du pare-brise
    fen = cv2.createHanningWindow((LARGEUR, y1 - y0), cv2.CV_32F)
    prec, dx = None, []
    while True:
        ok, im = c.read()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(im, (LARGEUR, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)[y0:y1].astype(np.float32)
        if prec is not None:
            (sx, _), rep = cv2.phaseCorrelate(prec, g, fen)
            dx.append(sx if rep > 0.02 else np.nan)
        prec = g
    c.release()
    dx = np.array(dx)
    cache.mkdir(parents=True, exist_ok=True)
    np.savez(f, dx=dx, fps=fps)
    return dx, fps


def segments(cap, seuil):
    """Changements de direction successifs d'un cap : [(i_debut, i_fin, variation signée)], avec hystérésis."""
    out, i0, ext, sens = [], 0, 0, 0
    for i in range(1, len(cap)):
        if sens == 0:
            if abs(cap[i] - cap[i0]) >= seuil:
                sens, ext = np.sign(cap[i] - cap[i0]), i
        elif (cap[i] - cap[ext]) * sens > 0:
            ext = i
        elif (cap[ext] - cap[i]) * sens >= seuil:
            out.append((i0, ext, float(cap[ext] - cap[i0])))
            i0, sens, ext = ext, -sens, i
    if sens != 0:
        out.append((i0, ext, float(cap[ext] - cap[i0])))
    return out


def aligner(a, b):
    """Aligne deux suites de variations signées (degrés). Rend (coût moyen, paires (i, j)), -1 = sans correspondant.
    Les bouts de la suite b (vidéo : avant le départ, après l'arrivée) peuvent rester sans correspondant sans coût."""
    na, nb = len(a), len(b)

    def cout(x, y):
        return 2.0 if x * y < 0 else abs(x - y) / (abs(x) + abs(y) + 10.0)

    def trou(x):
        return 0.5 + abs(x) / 90.0

    d = np.full((na + 1, nb + 1), np.inf)
    d[0, :] = 0.0                                              # début de la vidéo libre
    for i in range(1, na + 1):
        d[i, 0] = d[i - 1, 0] + trou(a[i - 1])
        for j in range(1, nb + 1):
            d[i, j] = min(d[i - 1, j - 1] + cout(a[i - 1], b[j - 1]), d[i - 1, j] + trou(a[i - 1]), d[i, j - 1] + trou(b[j - 1]))
    j = int(np.argmin(d[na, :]))                              # fin de la vidéo libre
    total, i, paires = float(d[na, j]), na, []
    while i > 0:
        if j > 0 and np.isclose(d[i, j], d[i - 1, j - 1] + cout(a[i - 1], b[j - 1])):
            paires.append((i - 1, j - 1)); i, j = i - 1, j - 1
        elif np.isclose(d[i, j], d[i - 1, j] + trou(a[i - 1])):
            paires.append((i - 1, -1)); i -= 1
        else:
            paires.append((-1, j - 1)); j -= 1
    return total / max(na, 1), paires[::-1]


def main():
    dossier = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE.parents[2]
    with open(RACINE / "data" / "processed" / "chaussee_precise.csv", encoding="utf-8") as f:
        r = [x for x in csv.DictReader(f) if x["zone"] == "es"]
    pk = np.array([float(x["pk_m"]) for x in r])
    p = np.array([[float(x["x_axe"]), float(x["y_axe"])] for x in r])
    d = np.gradient(p, axis=0)
    cap_t = np.degrees(savgol_filter(np.unwrap(np.arctan2(d[:, 1], d[:, 0])), 15, 2))       # + : vers la gauche
    seg_t = segments(cap_t, SEUIL_DEG)
    a = [s[2] for s in seg_t]
    print(f"tracé : {len(a)} changements de direction de plus de {SEUIL_DEG:.0f} deg, {sum(abs(x) for x in a):.0f} deg cumulés")
    bilan = {"seuil_deg": SEUIL_DEG, "trace": [{"pk_debut": round(float(pk[i])), "pk_fin": round(float(pk[j])), "angle_deg": round(v, 1)} for i, j, v in seg_t], "videos": {}}
    par_virage = {k: [] for k in range(len(a))}
    # une même vidéo peut exister en deux définitions : on ne garde que le plus gros fichier de chaque titre
    par_titre = {}
    for v in dossier.glob("*.mp4"):
        cle = v.stem[:40]
        if cle not in par_titre or v.stat().st_size > par_titre[cle].stat().st_size:
            par_titre[cle] = v
    for v in sorted(par_titre.values()):
        dx, fps = lacet_video(v, RACINE / "data" / "raw" / "video_lacet")
        dx = np.where(np.isnan(dx), 0.0, dx)
        w = int(fps) | 1
        cap_px = np.cumsum(savgol_filter(dx, w, 2))            # cap vu par la vidéo, en pixels
        meilleur = None
        tv = np.abs(np.diff(savgol_filter(cap_px, 2 * w + 1, 2))).sum()
        e0 = sum(abs(x) for x in a) / max(tv, 1e-6)
        for signe in (1.0, -1.0):
            for k in np.geomspace(0.4, 2.5, 28):
                capv = signe * e0 * k * cap_px
                b = [s[2] for s in segments(capv, SEUIL_DEG)]
                if len(b) < 10:
                    continue
                c, paires = aligner(a, b)
                if meilleur is None or c < meilleur[0]:
                    meilleur = (c, signe, e0 * k, b, paires)
        c, signe, ech, b, paires = meilleur
        app = [(i, j) for i, j in paires if i >= 0 and j >= 0 and a[i] * b[j] > 0]
        # échelle affinée sur les virages appariés, puis écarts
        ech2 = float(np.median([a[i] / b[j] for i, j in app])) if app else 1.0
        ecarts = []
        for i, j in app:
            bv = b[j] * ech2
            par_virage[i].append(bv)
            ecarts.append({"pk_debut": bilan["trace"][i]["pk_debut"], "pk_fin": bilan["trace"][i]["pk_fin"], "trace_deg": round(a[i], 1),
                           "video_deg": round(bv, 1), "ecart_deg": round(bv - a[i], 1)})
        sans = [bilan["trace"][i] for i, j in paires if j < 0]
        en_trop = [round(b[j] * ech2, 1) for i, j in paires if i < 0]
        opposes = [(bilan["trace"][i]["pk_debut"], round(a[i], 1), round(b[j] * ech2, 1)) for i, j in paires if i >= 0 and j >= 0 and a[i] * b[j] <= 0]
        e = np.array([x["ecart_deg"] for x in ecarts])
        bilan["videos"][v.name] = {"duree_s": round(len(dx) / fps, 1), "echelle_deg_par_px": round(ech * ech2, 4), "sens": "glissement vers la droite = virage à gauche" if signe > 0 else "glissement vers la gauche = virage à gauche",
                                   "changements_vus": len(b), "apparies": len(app), "virages_du_trace_non_retrouves": sans, "changements_video_sans_virage": en_trop,
                                   "sens_opposes": opposes, "ecart_median_deg": round(float(np.median(np.abs(e))), 1), "ecart_p90_deg": round(float(np.percentile(np.abs(e), 90)), 1),
                                   "virages": ecarts}
        print(f"\n{v.name[:64]} : {len(b)} changements vus, {len(app)} appariés sur {len(a)} ; écart médian {np.median(np.abs(e)):.1f} deg, p90 {np.percentile(np.abs(e), 90):.1f} deg")
        print("  virages du tracé non retrouvés :", [(s["pk_debut"], s["angle_deg"]) for s in sans][:10])
        print("  changements vus sans virage au tracé :", en_trop[:10], "| sens opposés :", opposes[:5])
    # synthèse : un virage est suspect si TOUTES les vidéos qui le voient s'écartent du tracé dans le même sens
    suspects = []
    for i, vals in par_virage.items():
        if len(vals) >= 2:
            ec = [x - a[i] for x in vals]
            if all(abs(x) > max(15.0, 0.3 * abs(a[i])) for x in ec) and len({np.sign(x) for x in ec}) == 1:
                suspects.append({**bilan["trace"][i], "videos_deg": [round(x, 1) for x in vals]})
    bilan["virages_suspects"] = suspects
    vus = [i for i, vals in par_virage.items() if vals]
    bilan["synthese"] = {"virages_du_trace": len(a), "retrouves_dans_au_moins_une_video": len(vus), "suspects": len(suspects)}
    (RACINE / "data" / "processed" / "comparaison_video.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\nsynthèse : {len(vus)} virages du tracé sur {len(a)} retrouvés dans au moins une vidéo ; suspects (toutes les vidéos s'écartent dans le même sens) : {len(suspects)}")
    for s in suspects:
        print("  ", s)


if __name__ == "__main__":
    main()
