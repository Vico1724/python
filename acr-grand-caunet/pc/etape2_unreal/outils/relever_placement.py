"""Recopie dans releves/placement_etape1.json le placement que le constructeur de l'étape 1 vient de calculer.

Pourquoi. Le mod de l'étape 1 (acr-ref stage-build) centre notre spéciale dans le niveau hôte : il calcule lui-même
(cx, cz, tx, tz) à partir de l'emprise de la route. Dès que la géométrie de la route change, même de quelques
centimètres, ce placement change aussi (8 cm après la régularisation du 12/11/2026). Le décor Unreal doit être posé
avec le MÊME placement que la physique, sinon route visible et route physique se décalent d'autant.

À lancer après chaque `4_construire.ps1`, avant `construire_niveau.py --placement ...` :
    python pc/etape2_unreal/outils/relever_placement.py [--rapport Z:/acrxs/construction/stage-grandcaunet.report.json]
Le script dit de combien le placement a bougé. S'il a bougé, le niveau Unreal est à reconstruire (les maillages déjà
importés restent bons : seule la pose change), puis à recuire.
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
RACINE = KIT.parents[1]
sys.path.insert(0, str(KIT / "scripts_editeur"))
import repere_unreal as R  # noqa: E402

RELEVE = KIT / "releves" / "placement_etape1.json"


def deplacement_m(ancien, neuf):
    """Déplacement (m) d'un point du décor quand on passe d'un placement à l'autre (le même partout : translation)."""
    t = math.radians(neuf["theta_deg"])
    c, s = math.cos(t), math.sin(t)
    dcx, dcz = neuf["cx"] - ancien["cx"], neuf["cz"] - ancien["cz"]
    dx = -(c * dcx + s * dcz) + neuf["tx"] - ancien["tx"]
    dz = -(-s * dcx + c * dcz) + neuf["tz"] - ancien["tz"]
    return dx, neuf["dy"] - ancien["dy"], dz


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rapport", default=r"Z:\acrxs\construction\stage-grandcaunet.report.json")
    ap.add_argument("--verifier", action="store_true", help="ne rien écrire ; code de sortie 1 si le relevé n'est plus à jour")
    a = ap.parse_args()
    rapport = json.loads(Path(a.rapport).read_text(encoding="utf-8-sig"))
    neuf = rapport["placement"]
    ancien = json.loads(RELEVE.read_text(encoding="utf-8")) if RELEVE.exists() else None
    if ancien and ancien["placement"]["theta_deg"] != neuf["theta_deg"]:
        print(f"ATTENTION : l'angle passe de {ancien['placement']['theta_deg']} à {neuf['theta_deg']} degrés")
    if ancien:
        d = deplacement_m(ancien["placement"], neuf)
        norme = math.hypot(d[0], d[2])
        print(f"déplacement du décor par rapport au relevé précédent : {norme * 100:.1f} cm en plan "
              f"(X {d[0] * 100:+.1f} cm, Y {d[2] * 100:+.1f} cm), {d[1] * 100:+.1f} cm en hauteur")
        if a.verifier:
            sys.exit(1 if norme > 0.005 or abs(d[1]) > 0.005 else 0)
    elif a.verifier:
        sys.exit(1)
    origine = json.loads((RACINE / "export" / "stage_ir" / "grand_caunet" / "stage.json").read_text(encoding="utf-8"))["coordinates"]["origin"]
    rep = R.charger_repere()
    pk0 = (rep["x0"], rep["y0"], rep["z0"])
    out = {"source": f"rubrique placement de {a.rapport} (acr-ref stage-build, étape 1), relevée le {time.strftime('%d/%m/%Y %H:%M')} "
                     f"par pc/etape2_unreal/outils/relever_placement.py",
           "lecture": "à passer à construire_niveau.py --placement : pose le décor dans le repère physique du mod de l'étape 1. "
                      "À relever après CHAQUE construction de l'étape 1 : le placement suit l'emprise de la route.",
           "placement": neuf, "origine_ir": origine, "options": rapport.get("options"),
           "points_de_controle_ue_cm": {
               f"depart_pk0_l93_{pk0[0]:.2f}_{pk0[1]:.2f}_{pk0[2]:.2f}": [round(v, 1) for v in R.l93_vers_unreal_acrxs(*pk0, origine, neuf)]}}
    if ancien and "reperes_du_mod" in ancien:
        out["reperes_du_mod_au_11_11_2026"] = ancien["reperes_du_mod"]
    RELEVE.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("écrit :", RELEVE.relative_to(RACINE).as_posix())


if __name__ == "__main__":
    main()
