"""Lance la chaîne du Grand Caunet (acr-grand-caunet/scripts) sur la Montée historique de Ceyreste.

Aucun script de traitement n'est recopié ici : ce lanceur pose ACR_EPREUVE sur le dossier de cette épreuve, et les
scripts du Grand Caunet lisent alors ses paramètres (epreuve.json), ses relevés (data/reference) et écrivent ses
produits (data/processed, figures, modele, export, paquet_unreal) dans ce dossier.

Exemples (depuis n'importe où) :
  python acr-montee-ceyreste/scripts/lancer.py --liste                 étapes de la chaîne
  python acr-montee-ceyreste/scripts/lancer.py --seulement 1 2         étapes choisies (numéros de tout_lancer.py)
  python acr-montee-ceyreste/scripts/lancer.py                         toute la chaîne 01 -> 16
  python acr-montee-ceyreste/scripts/lancer.py --script 17_diagnostic_trace.py [arguments]
                                                                       un script hors liste (diagnostics, figures)
  python acr-montee-ceyreste/scripts/lancer.py --script-ceyreste controle_ceyreste.py
                                                                       un script propre à cette épreuve (ce dossier)
"""
import os
import subprocess
import sys
from pathlib import Path

EPREUVE = Path(__file__).resolve().parents[1]
CODE = EPREUVE.parent / "acr-grand-caunet" / "scripts"


def main():
    env = {**os.environ, "ACR_EPREUVE": str(EPREUVE), "PYTHONUTF8": "1"}
    argv = sys.argv[1:]
    if argv[:1] == ["--script"]:
        cmd = [sys.executable, str(CODE / argv[1]), *argv[2:]]
        cwd = CODE
    elif argv[:1] == ["--script-ceyreste"]:
        cmd = [sys.executable, str(EPREUVE / "scripts" / argv[1]), *argv[2:]]
        cwd = EPREUVE / "scripts"
        env["PYTHONPATH"] = os.pathsep.join([str(CODE), env.get("PYTHONPATH", "")])
    else:
        cmd = [sys.executable, str(CODE / "tout_lancer.py"), *argv]
        cwd = CODE
    raise SystemExit(subprocess.run(cmd, cwd=cwd, env=env).returncode)


if __name__ == "__main__":
    main()
