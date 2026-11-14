r"""Conversions de repère Lambert-93 -> glTF du projet -> Unreal Engine (JAMAIS EXÉCUTÉ DANS UNREAL ; testé en Python
ordinaire sur le serveur pour le point de contrôle). Python pur, sans dépendance : utilisable dans l'éditeur Unreal
(Python de l'éditeur) comme en ligne de commande.

Trois repères :
  Lambert-93 (EPSG:2154) : x est, y nord, z altitude NGF, en mètres.
  glTF du projet (modele/*.glb, modele/repere.json) : X = x - x0 (est), Y = z - z0 (haut), Z = -(y - y0) (sud),
      mètres, main droite, +Y haut. (x0, y0, z0) = axe au PK 0.
  Unreal Engine : centimètres, Z haut, main gauche (X avant, Y droite, Z haut).
      Choix du projet : UE.X = est, UE.Y = sud, UE.Z = haut. Le triplet (est, sud, haut) est de main gauche, comme
      Unreal ; c'est aussi la convention d'ACR Extra Stages (physique (x, y, z) = UE (X, Z, Y) / 100, docs/decisions.md D3).
      Donc UE = 100 * (gX, gZ, gY).

Deux façons de placer le décor :
  mode "propre"      : notre niveau, origine au PK 0, comme ci-dessus.
  mode "acrxs"       : décor posé dans le repère physique choisi par leur constructeur (stage-build), pour coïncider
                       avec un BakedData produit par lui : physique = R_y(theta) * (ir - (cx, 0, cz)) + (tx, dy, tz),
                       ir = (x - x0_ir, z, -(y - y0_ir)) avec l'origine de export/stage_ir/.../stage.json
                       (coordinates.origin), puis UE cm = 100 * (px, pz, py). Valeurs lues dans la rubrique
                       "placement" du rapport de stage-build (…\construction\stage-grandcaunet.report.json).
"""
import json
import math
from pathlib import Path

RACINE = Path(__file__).resolve().parents[3]


def charger_repere(chemin=None):
    return json.loads(Path(chemin or RACINE / "modele" / "repere.json").read_text(encoding="utf-8"))


def l93_vers_gltf(x, y, z, rep):
    return (x - rep["x0"], z - rep["z0"], -(y - rep["y0"]))


def gltf_vers_unreal(gx, gy, gz):
    """glTF du projet (m) -> Unreal (cm) : UE = 100 * (gX, gZ, gY)."""
    return (gx * 100.0, gz * 100.0, gy * 100.0)


def l93_vers_unreal(x, y, z, rep):
    return gltf_vers_unreal(*l93_vers_gltf(x, y, z, rep))


def l93_vers_unreal_acrxs(x, y, z, origine_ir, placement):
    """origine_ir : {"lambert93_x_m", "lambert93_y_m"} de stage.json ; placement : rubrique "placement" du rapport."""
    ix, iy, iz = x - origine_ir["lambert93_x_m"], z, -(y - origine_ir["lambert93_y_m"])
    t = math.radians(placement["theta_deg"])
    c, s = math.cos(t), math.sin(t)
    dx, dz = ix - placement["cx"], iz - placement["cz"]
    px, py, pz = c * dx + s * dz + placement["tx"], iy + placement["dy"], -s * dx + c * dz + placement["tz"]
    return (px * 100.0, pz * 100.0, py * 100.0)


def lacet_unreal(cap_l93_deg, placement=None):
    """Lacet Unreal (degrés) d'un objet dont l'avant pointe au cap Lambert-93 donné (0 = nord, sens horaire).
    Mode propre : l'avant au nord = UE -Y, à l'est = UE +X ; le lacet Unreal tourne de +X vers +Y, donc
    lacet = cap - 90. Mode acrxs : en plus -theta (la rotation R_y vue en UE). À VÉRIFIER sur le PC avec un
    objet orienté (voir PROTOCOLE.md, E4)."""
    l = cap_l93_deg - 90.0
    if placement:
        l -= placement["theta_deg"]
    return (l + 180.0) % 360.0 - 180.0


if __name__ == "__main__":
    rep = charger_repere()
    print("repère :", {k: rep[k] for k in ("x0", "y0", "z0")})
    print("PK 0 (origine)            -> UE", l93_vers_unreal(rep["x0"], rep["y0"], rep["z0"], rep))
    # premier arbre de data/processed/arbres.csv (pin d'Alep, x 916565.25, y 6243787.75, sol 231.24 m)
    print("arbre 1 (916565.25, 6243787.75, 231.24) -> UE", tuple(round(v, 1) for v in l93_vers_unreal(916565.25, 6243787.75, 231.24, rep)))
    print("lacet d'un objet tourné vers l'est (cap 90) :", lacet_unreal(90.0))
