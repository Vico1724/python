"""Planches d'images de la reconnaissance autour de chaque paroi rocheuse relevée, pour en relire l'emprise exacte.

Pourquoi. Le premier relevé donnait chaque paroi à ±10 m, et parfois au PK de l'image où on l'APERCEVAIT devant la
voiture. L'essai en jeu du 13/11/2026 (quatrième version) a montré des parois décalées de 20 à 40 m, trop hautes, ou
posées là où il n'y a qu'un talus de terre. Ici, chaque paroi a sa suite d'images tous les PAS mètres, de 40 m avant à
30 m après : on lit le PK où le début de la roche arrive À HAUTEUR de la voiture (il sort de l'image par le côté), et
de même pour sa fin.

Les PK écrits sur les images sont ceux du calage de la reconnaissance (data/processed/calage_reco.json), non corrigés.

Usage (vidéo = fichier téléchargé : lancer avec « python -P » depuis un dossier neutre) :
    python -P scripts/24_planches_parois.py <vidéo de reconnaissance> [--pas 6] [--sortie figures/reco_parois]
                                            [--zones fichier.json]   (zones en plus : [{"pk": [a, b], "cote": "gauche"}])
Sortie : figures/reco_parois/paroi_NN_<pk début>-<pk fin>_<côté>_p<k>.jpg (hors dépôt) et index.json.
"""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

RACINE = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video")
    ap.add_argument("--pas", type=float, default=6.0)
    ap.add_argument("--avant", type=float, default=42.0)
    ap.add_argument("--apres", type=float, default=30.0)
    ap.add_argument("--sortie", default=str(RACINE / "figures" / "reco_parois"))
    ap.add_argument("--zones")
    a = ap.parse_args()
    tab = np.array(json.loads((RACINE / "data" / "processed" / "calage_reco.json").read_text(encoding="utf-8"))["table_t_s_pk_m"])
    parois = json.loads((RACINE / "data" / "reference" / "parois_rocheuses.json").read_text(encoding="utf-8"))["parois"]
    zones = [{"pk": [e["pk_debut_m"], e["pk_fin_m"]], "cote": e["cote"], "genre": e["genre"], "hauteur_m": e["hauteur_m"]} for e in parois]
    if a.zones:
        zones += json.loads(Path(a.zones).read_text(encoding="utf-8"))
    zones.sort(key=lambda z: z["pk"][0])
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    v = cv2.VideoCapture(a.video)
    fps = v.get(cv2.CAP_PROP_FPS)
    index = []
    for n, z in enumerate(zones, 1):
        pks = np.arange(z["pk"][0] - a.avant, z["pk"][1] + a.apres + 1e-6, a.pas)
        ims = []
        for p in pks:
            t = float(np.interp(p, tab[:, 1], tab[:, 0]))
            v.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * fps)))
            ok, im = v.read()
            if not ok:
                continue
            im = cv2.resize(im, (480, 270))
            dans = z["pk"][0] <= p <= z["pk"][1]
            cv2.rectangle(im, (0, 0), (150, 26), (0, 0, 0), -1)
            cv2.putText(im, f"PK {p:.0f}", (6, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255) if dans else (255, 255, 255), 2)
            ims.append(im)
        fichiers = []
        for k in range(0, len(ims), 12):
            lot = ims[k:k + 12]
            while len(lot) % 4:
                lot.append(np.zeros_like(ims[0]))
            planche = np.vstack([np.hstack(lot[i:i + 4]) for i in range(0, len(lot), 4)])
            nom = f"paroi_{n:02d}_{z['pk'][0]:.0f}-{z['pk'][1]:.0f}_{z['cote']}_p{k // 12 + 1}.jpg"
            cv2.imwrite(str(sortie / nom), planche, [cv2.IMWRITE_JPEG_QUALITY, 80])
            fichiers.append(nom)
        index.append({"numero": n, "pk_releve_m": z["pk"], "cote": z["cote"], "genre_releve": z.get("genre"), "hauteur_relevee_m": z.get("hauteur_m"),
                      "images_pk_m": [round(float(p)) for p in pks], "planches": fichiers})
    (sortie / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(index)} zones, {sum(len(x['planches']) for x in index)} planches dans {sortie}")


if __name__ == "__main__":
    main()
