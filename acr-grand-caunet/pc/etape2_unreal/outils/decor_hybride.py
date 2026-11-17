r"""Voie hybride (PROTOCOLE.md, E2b « voie H ») : écrit la liste de notre décor dans le repère du clone de Hafren
South produit par l'étape 1, pour que l'outil d'ACR Extra Stages l'inscrive dans le niveau :
  - nos maillages cuits (désignés par leur chemin /Game/..., livrés dans un conteneur à part), avec leur position ;
  - nos arbres, arbustes et piquets, groupés par maillage DU JEU, avec position, lacet et échelle.

Le décor du paquet est dans le repère « propre » (origine au PK 0, X est, Y sud, Z haut, cm). Le clone est dans le
repère physique choisi par leur constructeur (rubrique placement du rapport de stage-build) : rotation theta autour
de la verticale, puis translation. Un maillage posé sans rotation en repère propre reçoit donc le lacet -theta.
Le script vérifie cette règle sur chaque maillage avant d'écrire.

Le maillage et l'échelle de chaque plante sont choisis par scripts_editeur/attribution.py, comme dans
construire_niveau.py (même clé de tirage : mêmes choix).

EXÉCUTÉ sur le PC le 11/11/2026. Python ordinaire, sans dépendance.
Usage : python pc/etape2_unreal/outils/decor_hybride.py [--manifeste ...] [--etendue E4] [--placement rapport.json]
        [--sortie Z:\acrxs\unreal\hybride\decor_E4.json]
"""
import argparse
import csv
import json
import math
import os
import sys

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RACINE = os.path.dirname(os.path.dirname(KIT))
sys.path.insert(0, os.path.join(KIT, "scripts_editeur"))
import attribution as A  # noqa: E402
import repere_unreal as R  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifeste", default=os.path.join(KIT, "echantillon", "manifeste.json"))
    ap.add_argument("--etendue", default="E4")
    ap.add_argument("--placement", default=os.path.join(KIT, "releves", "placement_etape1.json"))
    ap.add_argument("--sortie")
    a = ap.parse_args()
    man = json.load(open(a.manifeste, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.manifeste))
    pl = json.load(open(a.placement, encoding="utf-8"))["placement"]
    org = json.load(open(os.path.join(RACINE, "export", "stage_ir", "grand_caunet", "stage.json"), encoding="utf-8"))["coordinates"]["origin"]
    rep = R.charger_repere()
    theta = pl["theta_deg"]

    def vers_clone(p_cm):
        """Point du repère propre (cm) -> repère du clone (cm)."""
        x, y, z = p_cm[0] / 100.0 + rep["x0"], rep["y0"] - p_cm[1] / 100.0, p_cm[2] / 100.0 + rep["z0"]
        return R.l93_vers_unreal_acrxs(x, y, z, org, pl)

    def lacet(l):
        return (l - theta + 180.0) % 360.0 - 180.0

    el = [e for e in man["elements"] if a.etendue in e["essais"] or a.etendue == "complet"]
    maillages = []
    for e in el:
        if e["type"] != "StaticMesh" or not e.get("acteur"):
            continue
        ac = e["acteur"]
        p = vers_clone(ac["position_cm"])
        l = lacet(ac["rotation_deg"][2])
        # contrôle : un point à 100 m à l'est du pivot, tourné par le lacet, doit tomber où la conversion le met
        t = math.radians(l)
        attendu = vers_clone([ac["position_cm"][0] + 10000.0, ac["position_cm"][1], ac["position_cm"][2]])
        obtenu = (p[0] + 10000.0 * math.cos(t), p[1] + 10000.0 * math.sin(t), p[2])
        ecart = max(abs(u - v) for u, v in zip(attendu, obtenu))
        if ecart > 1.0:
            raise SystemExit(f"{e['nom']} : le lacet {l:.2f} ne reproduit pas le placement (écart {ecart:.1f} cm)")
        maillages.append({"nom": e["nom"], "maillage": e["chemin_ue"], "position_cm": [round(v, 1) for v in p],
                          "lacet_deg": round(l, 3), "ombre": bool(ac.get("ombre_portee", True))})

    vegetation = A.charger(KIT)
    if vegetation is None:
        raise SystemExit("releves/maillages_vegetation.json absent : lancer outils/relever_jeu.py")
    pk = man["essais"].get(a.etendue, {}).get("pk_m")
    groupes = {}
    for e in el:
        if e["type"] != "InstanceGroup":
            continue
        dossier, nom_mesh = e["maillage_jeu"].rsplit("/", 1)
        cand = vegetation.get(dossier)
        with open(os.path.join(base, *e["fichier"].split("/")), encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if pk and not (pk[0] <= float(r["pk_m"]) <= pk[1]):
                    continue
                if cand:
                    d = r.get("diametre_m") or r.get("diametre_houppier_m")
                    choisi, s = A.choisir(cand, float(r["hauteur_voulue_m"]), float(d) if d else None, f"{e['nom']}:{r['id']}")
                else:
                    choisi, s = nom_mesh, 1.0
                p = vers_clone((float(r["x_cm"]), float(r["y_cm"]), float(r["z_cm"])))
                groupes.setdefault(f"{dossier}/{choisi}", []).append(
                    [round(p[0], 1), round(p[1], 1), round(p[2], 1), round(lacet(float(r["lacet_deg"])), 1), round(s, 3)])
    instances = [{"maillage": m, "nombre": len(v), "colonnes": ["x_cm", "y_cm", "z_cm", "lacet_deg", "echelle"], "instances": v}
                 for m, v in sorted(groupes.items())]
    sortie = a.sortie or os.path.join(r"Z:\acrxs\unreal\hybride", f"decor_{a.etendue}.json")
    os.makedirs(os.path.dirname(sortie), exist_ok=True)
    xs = [m["position_cm"] for m in maillages] + [i[:3] for g in instances for i in g["instances"]]
    out = {"description": "décor du Grand Caunet dans le repère du clone de Hafren South (voie hybride)",
           "etendue": a.etendue, "repere": "Unreal, cm, repère physique du constructeur d'ACR Extra Stages",
           "placement": pl, "lacet_des_maillages_deg": -theta,
           "bornes_cm": {"min": [round(min(p[k] for p in xs), 1) for k in range(3)], "max": [round(max(p[k] for p in xs), 1) for k in range(3)]},
           "maillages": maillages, "instances": instances}
    with open(sortie, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"{len(maillages)} maillages, {sum(g['nombre'] for g in instances)} instances en {len(instances)} groupes -> {sortie} "
          f"({os.path.getsize(sortie) // 1024} Ko)")
    print("bornes dans le clone (m) :", [round(v / 100) for v in out["bornes_cm"]["min"]], "à", [round(v / 100) for v in out["bornes_cm"]["max"]])


if __name__ == "__main__":
    main()
