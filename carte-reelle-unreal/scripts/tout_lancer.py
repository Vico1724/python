"""Enchaîne toute la chaîne pour une zone : 01 à 08 puis le contrôle du paquet.

Chaque étape tourne dans son propre processus avec les mêmes --zone, --sortie, --cache ; une étape
déjà faite pour la même zone.json est sautée (sauf --force). Affiche la première ligne du résumé de
chaque étape (et tout le résumé si une ligne signale un problème) ; la sortie complète est dans
<sortie>/journaux/tout_lancer.log. S'arrête à la première étape en échec.

Usage : python tout_lancer.py --zone zone.json --sortie DOSSIER [--cache DOSSIER] [--force]
        [--depuis 03] [--jusqua 07] [--mnt f.tif] [--ortho f.tif] [--sans-osm] [--vignettes] [--table t.csv]
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

ICI = Path(__file__).resolve().parent
ETAPES = ["01_emprise", "02_relief", "03_ortho", "04_vecteurs", "05_vegetation", "06_photos_rue",
          "07_lointain", "08_paquet_unreal", "controle_paquet"]
# options propres à une étape : (option de tout_lancer, étape, prend une valeur)
PROPRES = [("mnt", "02_relief", True), ("ortho", "03_ortho", True), ("sans_osm", "04_vecteurs", False),
           ("vignettes", "06_photos_rue", False), ("table", "08_paquet_unreal", True)]
SIGNAUX = ("ATTENTION", "ERREUR", "ÉCART", "injoignable", "Traceback")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--zone", required=True)
    ap.add_argument("--sortie", required=True)
    ap.add_argument("--cache")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--depuis", default="01", help="numéro de la première étape (01 à 08)")
    ap.add_argument("--jusqua", default="99", help="numéro de la dernière étape (le contrôle suit toujours 08)")
    ap.add_argument("--mnt")
    ap.add_argument("--ortho")
    ap.add_argument("--sans-osm", action="store_true")
    ap.add_argument("--vignettes", action="store_true")
    ap.add_argument("--table")
    a = ap.parse_args()
    sortie = Path(a.sortie).resolve()
    (sortie / "journaux").mkdir(parents=True, exist_ok=True)
    log = open(sortie / "journaux" / "tout_lancer.log", "w", encoding="utf-8")
    t0 = time.time()
    for e in ETAPES:
        num = e[:2] if e[0].isdigit() else "99"
        if num < a.depuis or (num > a.jusqua and not (e == "controle_paquet" and a.jusqua >= "08")):
            continue
        cmd = [sys.executable, str(ICI / f"{e}.py"), "--sortie", str(sortie)]
        if e == "controle_paquet":
            pass
        else:
            cmd += ["--zone", str(Path(a.zone).resolve())]
            if a.cache:
                cmd += ["--cache", str(Path(a.cache).resolve())]
            if a.force:
                cmd.append("--force")
        for opt, etape, valeur in PROPRES:
            v = getattr(a, opt)
            if etape == e and v:
                cmd += [f"--{opt.replace('_', '-')}"] + ([str(Path(v).resolve())] if valeur else [])
        t = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        sortie_txt = (r.stdout + r.stderr).strip()
        log.write(f"=== {e} ({time.time() - t:.0f} s, code {r.returncode})\n{sortie_txt}\n")
        log.flush()
        lignes = [l for l in sortie_txt.splitlines() if l.strip()]
        if r.returncode != 0:
            print(f"ÉCHEC {e} (code {r.returncode}) :")
            print("\n".join(lignes[-8:]))
            sys.exit(r.returncode)
        alerte = any(s in sortie_txt for s in SIGNAUX)
        print("\n".join(lignes[:5] if alerte else lignes[:1]))
    print(f"tout_lancer : terminé en {time.time() - t0:.0f} s ; détail : {sortie / 'journaux'}")


if __name__ == "__main__":
    main()
