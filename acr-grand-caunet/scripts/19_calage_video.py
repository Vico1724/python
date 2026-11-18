"""Calage d'une vidéo embarquée sur le tracé : à quelle distance du départ (PK) se trouve la caméra à chaque instant.

Pourquoi. Pour comparer une vidéo au modèle endroit par endroit (bords, obstacles, relief), il faut savoir quel point
de la route montre chaque image. Une vidéo de reconnaissances roule lentement et sans glisser : la rotation de la
caméra y suit fidèlement les virages de la route.

Méthode.
  1. Rotation de la caméra d'une image à la suivante : glissement horizontal du paysage, mesuré par corrélation de
     phase (fonction lacet_video de 18_comparaison_video.py), cumulé par pas de PAS_S seconde.
  2. Cap de la route tous les mètres, d'après l'axe de data/processed/chaussee_precise.csv.
  3. Plus court chemin (Viterbi) : à chaque pas de temps, la caméra avance de 0 à V_MAX x PAS_S mètres ; le coût d'une
     avance est l'écart entre la rotation vue par la caméra et le changement de cap de la route sur cette avance, plus
     un faible rappel vers une vitesse régulière (sur une ligne droite, la rotation ne dit rien de la position).
     L'échelle de la caméra (degrés par pixel) et son signe sont ceux qui donnent le chemin le moins coûteux.
  4. Repères facultatifs (--reperes fichier.json : [{"t_s": ..., "pk_m": ..., "repere": "..."}]) : points identifiés à
     l'image (pont, carrefour) ; le calage est corrigé pour passer par eux, en répartissant l'écart entre deux repères.
Précision : quelques mètres dans les virages ; sans repère, jusqu'à 20 à 30 m au milieu d'une longue ligne droite.

Usage : python scripts/19_calage_video.py <vidéo> --nom reco [--reperes data/reference/reperes_reco.json]
                                          [--planches 20]   (planches d'images tous les 20 m, dans figures/<nom>/)
Sorties : data/processed/calage_<nom>.json (table t_s -> pk_m, échelle, résidus).
"""
import argparse
import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.signal import savgol_filter

RACINE = Path(__file__).resolve().parents[1]
PAS_S = 0.2
V_MAX = 32.0            # m/s
SIGMA_DEG = 0.7         # écart admis entre rotation vue et changement de cap, par pas
RAPPEL = 0.004          # poids du rappel vers l'avance moyenne, par mètre d'écart au carré
FIN_LIBRE_M = 1000.0    # ... et se terminer n'importe où dans les derniers (arrivée lancée comprise)
DEPART_LIBRE_M = 450.0  # la vidéo peut commencer n'importe où dans les premiers mètres du tracé (approche comprise)

_spec = importlib.util.spec_from_file_location("s18", Path(__file__).with_name("18_comparaison_video.py"))
s18 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s18)


def route():
    with open(RACINE / "data" / "processed" / "chaussee_precise.csv", encoding="utf-8") as f:
        r = list(csv.DictReader(f))
    pk = np.array([float(x["pk_m"]) for x in r])
    p = np.array([[float(x["x_axe"]), float(x["y_axe"])] for x in r])
    d = np.gradient(p, axis=0)
    cap = np.degrees(savgol_filter(np.unwrap(np.arctan2(d[:, 1], d[:, 0])), 9, 2))      # + : vers la gauche
    return pk, cap


def viterbi(dtheta, cap, a_max, a_moy, depart, fin):
    """Chemin le moins coûteux : rend (coût total, indice de PK à chaque pas)."""
    n, k = len(cap), len(dtheta)
    c = np.full(n, np.inf)
    c[:depart] = 0.0
    choix = np.zeros((k, n), np.uint8)
    for t in range(k):
        meilleur = np.full(n, np.inf)
        arg = np.zeros(n, np.uint8)
        for a in range(a_max + 1):
            dcap = cap[a:] - cap[:n - a] if a else np.zeros(n)
            cout = c[:n - a] + ((dtheta[t] - dcap) / SIGMA_DEG) ** 2 + RAPPEL * (a - a_moy) ** 2
            m = cout < meilleur[a:]
            meilleur[a:][m] = cout[m]
            arg[a:][m] = a
        c, choix[t] = meilleur, arg
    j = fin + int(np.argmin(c[fin:]))                    # la vidéo se termine dans les derniers mètres du tracé
    total = float(c[j])
    chemin = np.zeros(k + 1, np.int64)
    chemin[k] = j
    for t in range(k - 1, -1, -1):
        j -= int(choix[t, j])
        chemin[t] = j
    return total, chemin


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video")
    ap.add_argument("--nom", required=True)
    ap.add_argument("--reperes")
    ap.add_argument("--planches", type=float, help="pas en mètres des images à extraire en planches")
    a = ap.parse_args()
    video = Path(a.video)
    dx, fps = s18.lacet_video(video, RACINE / "data" / "raw" / "video_lacet")
    dx = np.where(np.isnan(dx), 0.0, dx)
    par_pas = int(round(PAS_S * fps))
    k = len(dx) // par_pas
    dpx = dx[:k * par_pas].reshape(k, par_pas).sum(1)                       # glissement par pas, en pixels
    t_pas = np.arange(k + 1) * par_pas / fps
    pk, cap = route()
    a_max = int(np.ceil(V_MAX * PAS_S))
    a_moy = (pk[-1] - pk[0]) / max(k, 1)
    depart = int(np.searchsorted(pk, pk[0] + DEPART_LIBRE_M))
    fin = int(np.searchsorted(pk, pk[-1] - FIN_LIBRE_M))
    e0 = np.abs(np.diff(savgol_filter(cap, 31, 2))).sum() / max(np.abs(savgol_filter(dpx, 11, 2)).sum(), 1e-6)
    essais = []
    for signe in (1.0, -1.0):
        for f in np.geomspace(0.4, 6.0, 24):
            total, chemin = viterbi(signe * e0 * f * dpx, cap, a_max, a_moy, depart, fin)
            essais.append((total, signe * e0 * f, chemin))
    # affinage autour du meilleur
    essais.sort(key=lambda x: x[0])
    for f in np.linspace(0.93, 1.07, 9):
        total, chemin = viterbi(essais[0][1] * f * dpx, cap, a_max, a_moy, depart, fin)
        essais.append((total, essais[0][1] * f, chemin))
    total, echelle, chemin = min(essais, key=lambda x: x[0])
    # Biais de la mesure : même en ligne droite, le paysage glisse un peu d'une image à la suivante (caméra pas tout
    # à fait dans l'axe, objectif), et d'autant plus que la voiture va vite. Trois nombres pour toute la vidéo sont
    # ajustés sur le chemin trouvé : échelle, biais fixe, biais par mètre parcouru ; puis le chemin est recalculé.
    dtheta = echelle * dpx
    coef = np.array([echelle, 0.0, 0.0])
    for _ in range(3):
        avance = savgol_filter(np.diff(pk[chemin]).astype(float), 11, 2)
        dcap = cap[chemin[1:]] - cap[chemin[:-1]]
        A = np.column_stack([dpx, np.ones(k), avance])
        w = np.ones(k)
        for _ in range(4):                                   # moindres carrés robustes (poids de Huber)
            coef = np.linalg.lstsq(A * w[:, None], dcap * w, rcond=None)[0]
            r = np.abs(dcap - A @ coef)
            w = np.sqrt(np.where(r < 1.0, 1.0, 1.0 / np.maximum(r, 1e-9)))
        dtheta = A @ coef
        total, chemin = viterbi(dtheta, cap, a_max, a_moy, depart, fin)
    echelle = float(coef[0])
    pk_t = pk[chemin].astype(float)
    # le chemin avance par à-coups sur les lignes droites, où la rotation ne dit rien : vitesse lissée sur 3 secondes
    pk_t = np.maximum.accumulate(savgol_filter(pk_t, 15, 2))
    residu = dtheta - (cap[chemin[1:]] - cap[chemin[:-1]])
    reperes = []
    if a.reperes and Path(a.reperes).exists():
        reperes = sorted(json.loads(Path(a.reperes).read_text(encoding="utf-8")), key=lambda r: r["t_s"])
        tr = np.array([r["t_s"] for r in reperes])
        ecart = np.array([r["pk_m"] - float(np.interp(r["t_s"], t_pas, pk_t)) for r in reperes])
        for r, e in zip(reperes, ecart):
            r["ecart_avant_correction_m"] = round(float(e), 1)
        pk_t = pk_t + np.interp(t_pas, tr, ecart)
        pk_t = np.maximum.accumulate(pk_t)
    vit = np.gradient(pk_t, t_pas) * 3.6
    # Angle de chaque changement de direction du tracé (plus de 12 degrés), et angle vu par la caméra sur le même
    # intervalle de route. Le calage ne peut pas masquer un écart local : il n'a que trois nombres pour toute la vidéo.
    cap_v = np.r_[0.0, np.cumsum(dtheta)]
    virages = []
    for i0, i1, _ in s18.segments(savgol_filter(cap, 15, 2), 12.0):
        pa, pb = pk[i0] - 8.0, pk[i1] + 8.0
        if pa < pk_t[0] + 10 or pb > pk_t[-1] - 10:
            continue
        ta, tb = np.interp(pa, pk_t, t_pas), np.interp(pb, pk_t, t_pas)
        vr = float(np.interp(pb, pk, cap) - np.interp(pa, pk, cap))
        vv = float(np.interp(tb, t_pas, cap_v) - np.interp(ta, t_pas, cap_v))
        virages.append({"pk_debut": round(float(pk[i0])), "pk_fin": round(float(pk[i1])), "sens": "gauche" if vr > 0 else "droite",
                        "trace_deg": round(vr, 1), "camera_deg": round(vv, 1), "ecart_deg": round(vv - vr, 1)})
    ec = np.array([v["ecart_deg"] for v in virages])
    bilan = {"video": video.name, "duree_s": round(len(dx) / fps, 1), "images_par_s": round(fps, 3), "pas_s": PAS_S,
             "echelle_deg_par_px": round(float(echelle), 5), "cout_moyen_par_pas": round(total / k, 3),
             "residu_de_rotation_deg": {"ecart_type": round(float(residu.std()), 3), "p95": round(float(np.percentile(np.abs(residu), 95)), 3)},
             "pk_au_debut_m": round(float(pk_t[0]), 1), "pk_a_la_fin_m": round(float(pk_t[-1]), 1),
             "vitesse_kmh": {"mediane": round(float(np.median(vit)), 1), "max": round(float(vit.max()), 1)},
             "biais_fixe_deg_par_pas": round(float(coef[1]), 4), "biais_par_metre_deg": round(float(coef[2]), 5),
             "derive_totale_deg": round(float(cap_v[-1] - (cap[chemin[-1]] - cap[chemin[0]])), 1),
             "virages": {"nombre": len(virages), "ecart_absolu_median_deg": round(float(np.median(np.abs(ec))), 1),
                         "ecart_p90_deg": round(float(np.percentile(np.abs(ec), 90)), 1), "ecart_max_deg": round(float(np.abs(ec).max()), 1),
                         "detail": virages},
             "reperes": reperes,
             "table_t_s_pk_m": [[round(float(t), 2), round(float(p), 1)] for t, p in zip(t_pas[::5], pk_t[::5])]}
    out = RACINE / "data" / "processed" / f"calage_{a.nom}.json"
    out.write_text(json.dumps(bilan, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print({k_: v for k_, v in bilan.items() if k_ not in ("table_t_s_pk_m", "reperes", "virages")})
    print("virages :", {k_: v for k_, v in bilan["virages"].items() if k_ != "detail"})
    for v in sorted(virages, key=lambda v: -abs(v["ecart_deg"]))[:10]:
        print(f"   PK {v['pk_debut']:5d}-{v['pk_fin']:5d} {v['sens']:6s} tracé {v['trace_deg']:+7.1f}  caméra {v['camera_deg']:+7.1f}  écart {v['ecart_deg']:+6.1f} deg")
    for r in reperes:
        print(f"  repère {r['t_s']:6.1f} s -> PK {r['pk_m']:6.0f} ({r.get('repere', '')}) : écart avant correction {r['ecart_avant_correction_m']:+.0f} m")
    print("écrit :", out.relative_to(RACINE).as_posix())
    if a.planches:
        import cv2
        dossier = RACINE / "figures" / a.nom
        dossier.mkdir(parents=True, exist_ok=True)
        for f in dossier.glob("planche_*.jpg"):
            f.unlink()
        cap_v = cv2.VideoCapture(str(video))
        cibles = np.arange(np.ceil(max(pk_t[0], 0.0) / a.planches) * a.planches, pk_t[-1], a.planches)
        temps = np.interp(cibles, pk_t, t_pas)
        ims = []
        for p, t in zip(cibles, temps):
            cap_v.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * fps)))
            ok, im = cap_v.read()
            if not ok:
                continue
            h, w = im.shape[:2]
            im = cv2.resize(im[: int(h * 0.80)], (640, int(640 * 0.80 * h / w)), interpolation=cv2.INTER_AREA)   # sans le tableau de bord
            cv2.rectangle(im, (0, 0), (250, 30), (0, 0, 0), -1)
            cv2.putText(im, f"PK {p:.0f}  {int(t // 60)}:{t % 60:04.1f}", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
            ims.append((p, im))
        for i in range(0, len(ims), 6):
            lot = [x[1] for x in ims[i:i + 6]]
            while len(lot) < 6:
                lot.append(np.zeros_like(lot[0]))
            cv2.imwrite(str(dossier / f"planche_{int(ims[i][0]):04d}.jpg"), np.vstack([np.hstack(lot[:3]), np.hstack(lot[3:])]),
                        [cv2.IMWRITE_JPEG_QUALITY, 82])
        print(f"{len(ims)} images en planches de 6 dans figures/{a.nom}/")


if __name__ == "__main__":
    main()
