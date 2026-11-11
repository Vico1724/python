"""Essai HORS D'UNREAL de scripts_editeur/construire_niveau.py avec le faux module unreal (outils/faux_unreal).
Vérifie que la logique de parcours du manifeste tourne de bout en bout et que ses comptes sont justes. Ne prouve
rien sur l'API réelle d'Unreal (A_VERIFIER.md).
Usage : python3 pc/etape2_unreal/outils/essai_construire.py [manifeste.json]   (défaut : l'échantillon)
"""
import importlib
import json
import os
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(ICI)
sys.path.insert(0, os.path.join(ICI, "faux_unreal"))
sys.path.insert(0, os.path.join(KIT, "scripts_editeur"))
os.environ["GC_ESSAI_HORS_UNREAL"] = "1"
os.environ["GC_FAUX_SAVED"] = tempfile.mkdtemp()


def lancer(manifeste, args, axes="X,Z,Y"):
    os.environ["GC_FAUX_AXES"] = axes
    import unreal
    importlib.reload(unreal)
    # simule creer_factices.py : les maillages du jeu existent dans le projet (cubes), ainsi que M_Simple et la
    # variante modèle du jeu qui sert de parent à nos variantes (factices.json)
    for e in json.load(open(manifeste, encoding="utf-8"))["elements"]:
        if e["type"] == "InstanceGroup":
            unreal.ASSETS[e["maillage_jeu"]] = unreal.StaticMesh(e["maillage_jeu"], [-50] * 3, [50] * 3, "cube")
    for x in json.load(open(os.path.join(KIT, "factices.json"), encoding="utf-8"))["factices"]:
        if x["type"] == "StaticMesh":
            unreal.ASSETS.setdefault(x["objet"], unreal.StaticMesh(x["objet"], [-50] * 3, [50] * 3, "cube"))
        elif x["type"] == "Material":
            unreal.ASSETS.setdefault(x["objet"], unreal.Material(x["objet"]))
        elif x["type"] == "MaterialInstanceConstant":
            unreal.ASSETS.setdefault(x["objet"], unreal.MaterialInstanceConstant(x["objet"]))
    sys.argv = ["construire_niveau.py", "--manifeste", manifeste] + args
    cn = importlib.import_module("construire_niveau")
    cn = importlib.reload(cn)
    cn.unreal = unreal
    return cn.main(), unreal


def verifier(manifeste, etendue):
    man = json.load(open(manifeste, encoding="utf-8"))
    el = [e for e in man["elements"] if etendue in e["essais"] or etendue == "complet"]
    mesh = [e for e in el if e["type"] == "StaticMesh" and e.get("acteur")]
    r, u = lancer(manifeste, ["--etendue", etendue, "--mire"])
    pk = man["essais"][etendue].get("pk_m")
    n_inst = 0
    base = os.path.dirname(manifeste)
    for e in el:
        if e["type"] == "InstanceGroup":
            with open(os.path.join(base, e["fichier"]), encoding="utf-8") as f:
                next(f)
                for ligne in f:
                    p = float(ligne.split(",")[6])
                    n_inst += (not pk) or (pk[0] <= p <= pk[1])
    erreurs = []
    if r["maillages"] != len(mesh) + 3:
        erreurs.append(f"maillages {r['maillages']} != {len(mesh)} + 3 (mire)")
    if r["acteurs"] != len(mesh):
        erreurs.append(f"acteurs {r['acteurs']} != {len(mesh)}")
    if r["verdicts_bornes"]["conformes"] != len(mesh) or r["verdicts_bornes"]["differents"]:
        erreurs.append(f"bornes : {r['verdicts_bornes']['conformes']} conformes sur {len(mesh)}")
    if r["instances"] != n_inst:
        erreurs.append(f"instances {r['instances']} != {n_inst}")
    parasites = [c for c in u.ASSETS if "parasite" in c]
    if parasites:
        erreurs.append(f"matériaux parasites restés : {parasites[:3]}")
    sans_tex = [c for c, o in u.ASSETS.items() if o.get_class().get_name() == "MaterialInstanceConstant"
                and c.startswith(man["chemins"]["racine"]) and not o.props.get("textures")]     # nos variantes, pas les factices
    if sans_tex:
        erreurs.append(f"variantes sans texture : {sans_tex[:3]}")
    sans_mat = [c for c, o in u.ASSETS.items() if o.get_class().get_name() == "StaticMesh" and "/Mire/" not in c and c.startswith(man["chemins"]["racine"])
                and not o.materiaux]
    if sans_mat:
        erreurs.append(f"maillages sans variante : {sans_mat[:3]}")
    print(f"--- {etendue} : {r['maillages']} maillages, {r['textures']} textures, {r['variantes']} variantes, "
          f"{r['acteurs']} acteurs, {r['instances']} instances, alertes {len(r['alertes'])} -> "
          f"{'OK' if not erreurs else erreurs}")
    return not erreurs


def verifier_releves(manifeste):
    """Corrections tirées des relevés du jeu (PROTOCOLE.md § 0 bis), avec --parent jeu :
    - chaque variante a pour parent la variante modèle du jeu, jamais M_Simple, et règle un relief ;
    - aucune instance ne désigne un maillage que le relevé donne pour une souche, et aucune plaque de couvre-sol
      n'est mise à l'échelle sur sa hauteur."""
    factices = json.load(open(os.path.join(KIT, "factices.json"), encoding="utf-8"))["factices"]
    modele = next((x["objet"] for x in factices if x.get("role") == "modele_m_simple"), None)
    releve = os.path.join(KIT, "releves", "maillages_vegetation.json")
    if not modele or not os.path.exists(releve):
        print("--- relevés du jeu absents (outils/relever_jeu.py, liste_factices.py) : corrections non vérifiées")
        return True
    r, u = lancer(manifeste, ["--etendue", "E4", "--parent", "jeu"])
    racine = json.load(open(manifeste, encoding="utf-8"))["chemins"]["racine"]
    nos_mi = {c: o for c, o in u.ASSETS.items() if o.get_class().get_name() == "MaterialInstanceConstant" and c.startswith(racine)}
    erreurs = []
    # variantes qui héritent d'un matériau du jeu (asphalte de Bollène...) : ce parent-là, et aucune texture à elles
    speciaux = {nom: x["objet"] for x in factices if x.get("role") == "parent_du_jeu" for nom in x.get("pour", [])}

    def attendu(c):
        return u.ASSETS[speciaux.get(c.rsplit("/", 1)[1], modele)]

    mauvais_parent = [c for c, o in nos_mi.items() if getattr(o, "parent", None) is not attendu(c)]
    if mauvais_parent:
        erreurs.append(f"variantes sans le parent du jeu attendu : {mauvais_parent[:3]}")
    sans_relief = [c for c, o in nos_mi.items() if c.rsplit("/", 1)[1] not in speciaux
                   and "Simple_Normal_Texture" not in o.props.get("textures", {})]
    if sans_relief:
        erreurs.append(f"variantes sans relief : {sans_relief[:3]}")
    if r["variantes_sur_le_modele_du_jeu"] + r["variantes_sur_un_materiau_du_jeu"] != r["variantes"]:
        erreurs.append(f"{r['variantes_sur_le_modele_du_jeu']} + {r['variantes_sur_un_materiau_du_jeu']} variantes sur un parent du jeu pour {r['variantes']}")
    veg = json.load(open(releve, encoding="utf-8"))["dossiers"]
    hauts = {d + "/" + n: v[0] for d, m in veg.items() for n, v in m.items()}
    plaques = {d for d, m in veg.items() if max(v[0] for v in m.values()) < 30}
    chemin_de = {id(o): c for c, o in u.ASSETS.items()}
    vus = 0
    for a in u.ACTEURS:
        for comp in a.props.get("composants", []):
            chemin = chemin_de.get(id(comp.props.get("mesh")))
            if chemin not in hauts:
                continue
            vus += 1
            dossier = chemin.rsplit("/", 1)[0]
            if dossier not in plaques and hauts[chemin] < 150:
                erreurs.append(f"{a.get_actor_label()} désigne une souche ({hauts[chemin]} cm)")
            ech = [t.scale.x for t in comp.props.get("instances", [])]
            if ech and max(ech) > 6:
                erreurs.append(f"{a.get_actor_label()} : échelle jusqu'à {max(ech):.1f}")
    if not vus:
        erreurs.append("aucun groupe d'instances de végétation trouvé dans le niveau")
    print(f"--- relevés du jeu, --parent jeu : {r['variantes_sur_le_modele_du_jeu']} variantes sur la variante modèle, "
          f"{r['reliefs_plats_ajoutes']} reliefs plats ajoutés, {r['instances_reattribuees']} instances réattribuées sur "
          f"{r['instances']} -> {'OK' if not erreurs else erreurs}")
    return not erreurs


def main():
    manifeste = sys.argv[1] if len(sys.argv) > 1 else os.path.join(KIT, "echantillon", "manifeste.json")
    ok = True
    for etendue in ("E3", "E4") + (("complet",) if len(sys.argv) > 1 else ()):
        ok &= verifier(manifeste, etendue)
    # une mire qui révèle d'autres axes doit arrêter le script avant toute construction
    r, u = lancer(manifeste, ["--etendue", "E3", "--mire"], axes="Z,X,Y")
    arret = r["acteurs"] == 0 and r.get("mire", {}).get("valeur_mesuree") == "Z,X,Y"
    print(f"--- mire avec des axes différents : {'arrêt correct' if arret else 'ÉCHEC'} ({r.get('mire')})")
    ok &= arret
    # paquet corrigé par reaxer_paquet.py pour un importeur « Z,-X,Y » : tout doit redevenir conforme
    import shutil
    import subprocess
    copie = os.path.join(tempfile.mkdtemp(), "paquet")
    shutil.copytree(os.path.dirname(os.path.abspath(manifeste)), copie)
    subprocess.run([sys.executable, os.path.join(ICI, "reaxer_paquet.py"), os.path.join(copie, "manifeste.json"),
                    "--axes", "Z,-X,Y"], check=True)
    r, u = lancer(os.path.join(copie, "manifeste.json"), ["--etendue", "E4", "--mire"], axes="Z,-X,Y")
    bon = r["acteurs"] > 0 and not r["verdicts_bornes"]["differents"]
    print(f"--- paquet réaxé (Z,-X,Y) : {r['acteurs']} acteurs, {r['verdicts_bornes']['conformes']} bornes conformes -> "
          f"{'OK' if bon else 'ÉCHEC'}")
    ok &= bon
    ok &= verifier_releves(manifeste)
    print("ESSAI RÉUSSI" if ok else "ESSAI EN ÉCHEC")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
