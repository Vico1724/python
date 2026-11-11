"""REMPLACÉ PAR construire_niveau.py (piloté par le manifeste de scripts/16_paquet_unreal.py), qui fait la même chose
au complet ; ce squelette est gardé pour mémoire et ne doit plus être lancé.

JAMAIS EXÉCUTÉ. Python de l'éditeur Unreal 5.6. Pose les arbres de data/processed/arbres.csv dans le niveau
ouvert, en instances : un acteur par maillage du jeu (colonne famille_jeu / element_jeu_propose), portant un
composant HierarchicalInstancedStaticMeshComponent qui désigne le FACTICE de ce maillage (creer_factices.py) ; le
jeu y substituera son vrai maillage.

Placement : repere_unreal.py (mode "propre", ou mode "acrxs" si --placement est donné, pour coïncider avec un
BakedData produit par leur constructeur). Point de contrôle (repère du 11/11/2026, modele/repere.json
x0 917008.49, y0 6241030.6, z0 398.55) : le premier arbre du fichier, pin d'Alep en (916565.25, 6243787.75, sol
231.24 m), doit être posé en UE (-44324.0, -275715.0, -16731.0) cm en mode "propre". Recalculer avec
python3 repere_unreal.py si le repère a changé.

Échelle : hauteur mesurée / hauteur du maillage du jeu. Les hauteurs ont été relevées sur le PC le 11/11/2026
(outils/relever_jeu.py -> hauteurs_maillages.json, en cm) ; outils/reattribuer_arbres.py en a tiré
arbres_jeu.csv.gz, où chaque arbre a un maillage de taille voisine et son échelle. Ce script lit ce fichier s'il
existe ; sinon arbres.csv et hauteurs_maillages.json ; sans aucun des deux : échelle 1.
Lacet : aléatoire (graine fixe) : nos arbres n'ont pas d'orientation mesurée.

Incertitude : la création d'un composant d'instances sur un acteur depuis Python passe ici par
SubobjectDataSubsystem ; si l'appel est refusé dans cette version, utiliser à la place l'outil Foliage de l'éditeur
ou un Blueprint d'acteur portant le composant (voir la documentation Python d'Unreal 5.6 sur le PC).
Usage : py "…/poser_arbres.py" [--placement rapport.json] [--pk-min 0 --pk-max 200] [--max 50000]
"""
import argparse
import csv
import gzip
import json
import os
import random
import sys

import unreal

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import repere_unreal as R  # noqa: E402

RACINE = os.path.abspath(os.path.join(ICI, "..", "..", ".."))


def composant_instances(acteur, nom):
    sds = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    racine = sds.k2_gather_subobject_data_for_instance(acteur)[0]
    p = unreal.AddNewSubobjectParams(parent_handle=racine, new_class=unreal.HierarchicalInstancedStaticMeshComponent)
    h, raison = sds.add_new_subobject(p)
    if not raison.is_empty():
        raise RuntimeError(f"composant refusé : {raison}")
    sds.rename_subobject(h, unreal.Text(nom))
    return unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--placement")
    ap.add_argument("--pk-min", type=float, default=-1e9)
    ap.add_argument("--pk-max", type=float, default=1e9)
    ap.add_argument("--max", type=int, default=100000)
    a = ap.parse_args(sys.argv[1:])
    rep = R.charger_repere()
    pl = org = None
    if a.placement:
        rapport = json.load(open(a.placement, encoding="utf-8"))
        pl = rapport["placement"]
        org = json.load(open(os.path.join(RACINE, "export", "stage_ir", "grand_caunet", "stage.json"), encoding="utf-8"))["coordinates"]["origin"]
    hfile = os.path.join(ICI, "..", "hauteurs_maillages.json")
    hauteurs = json.load(open(hfile, encoding="utf-8")) if os.path.exists(hfile) else {}
    if not hauteurs:
        unreal.log_warning("hauteurs_maillages.json absent : échelle 1 pour tous les arbres")
    # arbres_jeu.csv.gz (outils/reattribuer_arbres.py) : maillage choisi selon la hauteur réelle des maillages du jeu,
    # colonnes element_jeu et echelle. À défaut, arbres.csv, dont le maillage a été tiré sans connaître les hauteurs.
    reattribue = os.path.join(ICI, "..", "arbres_jeu.csv.gz")
    if os.path.exists(reattribue):
        lignes, col = csv.DictReader(gzip.open(reattribue, "rt", encoding="utf-8")), "element_jeu"
    else:
        unreal.log_warning("arbres_jeu.csv.gz absent : maillages de arbres.csv, dont certains sont des souches (reattribuer_arbres.py)")
        lignes, col = csv.DictReader(open(os.path.join(RACINE, "data", "processed", "arbres.csv"), encoding="utf-8")), "element_jeu_propose"
    rng = random.Random(1)
    groupes = {}
    for r in lignes:
        if not (a.pk_min <= float(r["pk_m"]) <= a.pk_max):
            continue
        groupes.setdefault((r["famille_jeu"], r[col]), []).append(r)
    total = 0
    for (famille, nom), arbres in sorted(groupes.items()):
        mesh = unreal.load_asset(f"/Game/{famille}/{nom}")
        if mesh is None:
            unreal.log_warning(f"{famille}/{nom} : factice absent (creer_factices.py)")
            continue
        acteur = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0))
        acteur.set_actor_label(f"GC_Arbres_{nom}")
        comp = composant_instances(acteur, f"ISM_{nom}")
        comp.set_static_mesh(mesh)
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)   # obstacles : BakedData seulement
        h_mesh = hauteurs.get(nom)
        for r in arbres[: max(0, a.max - total)]:
            x, y, z = float(r["x_l93"]), float(r["y_l93"]), float(r["z_sol_m"])
            p = R.l93_vers_unreal_acrxs(x, y, z, org, pl) if pl else R.l93_vers_unreal(x, y, z, rep)
            s = float(r["echelle"]) if r.get("echelle") else (float(r["hauteur_m"]) * 100.0 / h_mesh if h_mesh else 1.0)
            t = unreal.Transform(location=unreal.Vector(*p), rotation=unreal.Rotator(roll=0.0, pitch=0.0, yaw=rng.uniform(-180, 180)),
                                 scale=unreal.Vector(s, s, s))
            comp.add_instance(t)
            total += 1
        unreal.log(f"{nom} : {len(arbres)} arbres")
    unreal.log(f"arbres posés : {total}")


main()
