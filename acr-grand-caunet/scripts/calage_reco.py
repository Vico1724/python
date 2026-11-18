"""Correction du calage de la vidéo de reconnaissance : PK réel d'un objet relevé sur cette vidéo.

Le calage par les virages (19_calage_video.py) dérive de 0 à 24 m selon l'endroit ; data/reference/calage_reco_reperes.json
donne l'écart mesuré en vingt points connus par ailleurs (ponts du relevé laser, débouchés de pistes de l'IGN).
"""
import json
from pathlib import Path

import numpy as np

_R = None


def corrige(pk):
    """PK réel pour un PK lu sur la vidéo de reconnaissance (nombre ou tableau)."""
    global _R
    if _R is None:
        f = Path(__file__).resolve().parents[1] / "data" / "reference" / "calage_reco_reperes.json"
        _R = np.array([[r[0], r[1]] for r in json.loads(f.read_text(encoding="utf-8"))["reperes"]], float)
    pk = np.asarray(pk, float)
    return pk + np.interp(pk, _R[:, 0], _R[:, 1])
