"""Passe la spéciale hôte de « terre » à « asphalte » dans la table des variantes du jeu (DT_TracksVariants).

Demande du directeur (13/11/2026) : le jeu classe la spéciale en terre et n'y propose que des pneus terre, alors que
le Grand Caunet est tout en asphalte. La spéciale remplace la variante galloise WelesS4HafrenSouthFullForward, dont la
ligne porte : SurfaceTypes = Gravel 100 %, CarSetupDefaultSurfaceType = Gravel, TireCompounds = GravelOnly, et trois
secteurs en Gravel. Les spéciales sur asphalte du jeu portent Tarmac et TarmacSnow (lu dans la table d'origine).

Ce script ne touche qu'à la COPIE de la table que le constructeur vient d'écrire dans le dossier du mod (paquet
« legacy » : .uasset et .uexp), jamais aux archives du jeu. Dans cette ligne et elle seule, il remplace les renvois
au nom « Gravel » par « Tarmac » et « GravelOnly » par « TarmacSnow ». Les deux noms existent déjà dans la table (les
autres lignes s'en servent), et un renvoi de nom a une taille fixe : le fichier garde sa longueur.

Il refuse d'écrire si le nombre de renvois trouvés n'est pas celui attendu (5 et 1).

La table de départ peut être celle du jeu ou celle d'un mod « registre » qui la livre déjà (cas du PC du directeur :
pakchunk99-SandoRegistry_2_P, qui porte les lignes de BioBio ; il a autorisé le 13/11/2026 qu'on parte de cette table,
voir 6_table_asphalte.ps1). --suivante donne la ligne qui suit la nôtre dans la table, pour borner la nôtre sans rien
supposer du nom des autres lignes ; --longueur-km remplace aussi la longueur affichée au menu (4,8 km d'origine).

Usage : python pneus_asphalte.py <dossier du mod> [--ligne WelesS4HafrenSouthFullForward] [--suivante NOM]
                                 [--longueur-km 6.738] [--essai]
"""
import argparse
import struct
import sys
from pathlib import Path

REL = Path("acr") / "Content" / "Data" / "Database" / "Main" / "TrackSelection" / "DT_TracksVariants"
ECHANGES = (("Gravel", "Tarmac", 5), ("GravelOnly", "TarmacSnow", 1))


def table_des_noms(b):
    """Noms du paquet, dans l'ordre : la plus longue suite d'entrées (longueur, texte terminé par zéro, 4 octets)."""
    meilleur = []
    i = 0
    while i < len(b) - 8:
        noms, j = [], i
        while j + 4 <= len(b):
            n = struct.unpack_from("<i", b, j)[0]
            if 1 < n <= 512 and j + 4 + n + 4 <= len(b) and b[j + 4 + n - 1] == 0:
                txt = b[j + 4:j + 4 + n - 1]
                if not all(32 <= c < 127 for c in txt):
                    break
                noms.append(txt.decode("ascii"))
                j += 4 + n + 4
            elif -512 <= n < -1 and j + 4 - 2 * n + 4 <= len(b):
                noms.append(b[j + 4:j + 4 - 2 * n - 2].decode("utf-16-le", "replace"))
                j += 4 - 2 * n + 4
            else:
                break
        if len(noms) > len(meilleur):
            meilleur = noms
        i = j if len(noms) > 8 else i + 1
    return meilleur


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mod")
    ap.add_argument("--ligne", default="WelesS4HafrenSouthFullForward")
    ap.add_argument("--suivante", help="nom de la ligne qui suit la nôtre dans la table")
    ap.add_argument("--longueur-km", type=float, help="longueur à écrire à la place de celle de la ligne (4,8 km)")
    ap.add_argument("--longueur-d-origine-km", type=float, default=4.8)
    ap.add_argument("--essai", action="store_true", help="contrôle sans écrire")
    a = ap.parse_args()
    base = Path(a.mod) / REL
    f_asset, f_exp = base.with_suffix(".uasset"), base.with_suffix(".uexp")
    if not (f_asset.exists() and f_exp.exists()):
        sys.exit(f"table absente de {a.mod} : le constructeur doit la livrer (4_construire.ps1 -Asphalte)")
    noms = table_des_noms(f_asset.read_bytes())
    rang = {n: i for i, n in enumerate(noms)}
    manque = [n for n in (a.ligne, "Gravel", "Tarmac", "GravelOnly", "TarmacSnow") if n not in rang]
    if manque:
        sys.exit(f"noms absents de la table ({len(noms)} noms lus) : {manque}")
    exp = bytearray(f_exp.read_bytes())
    cle = struct.pack("<ii", rang[a.ligne], 0)
    debut = exp.find(cle)
    if debut < 0 or exp.find(cle, debut + 8) >= 0:
        sys.exit(f"ligne {a.ligne} introuvable ou trouvée plusieurs fois dans le .uexp")
    # fin de la ligne : la clé de ligne suivante la plus proche (toute ligne dont le nom finit par Forward ou Reverse)
    if a.suivante:
        if a.suivante not in rang:
            sys.exit(f"ligne suivante {a.suivante} absente des noms de la table")
        fin = exp.find(struct.pack("<ii", rang[a.suivante], 0), debut + 8)
        if fin < 0:
            sys.exit(f"ligne suivante {a.suivante} introuvable après {a.ligne} dans le .uexp")
    else:
        fins = [exp.find(struct.pack("<ii", i, 0), debut + 8) for n, i in rang.items() if n != a.ligne and n.endswith(("Forward", "Reverse"))]
        fins = [x for x in fins if x > 0]
        fin = min(fins) if fins else len(exp)
    bilan = []
    for vieux, neuf, attendu in ECHANGES:
        motif, rempl = struct.pack("<ii", rang[vieux], 0), struct.pack("<ii", rang[neuf], 0)
        pos, k = [], debut + 8
        while True:
            k = exp.find(motif, k, fin)
            if k < 0:
                break
            pos.append(k)
            k += 8
        bilan.append((vieux, neuf, len(pos), attendu))
        if len(pos) != attendu:
            sys.exit(f"{vieux} : {len(pos)} renvois trouvés dans la ligne (octets {debut} à {fin}), {attendu} attendus ; rien n'est écrit")
        for k in pos:
            exp[k:k + 8] = rempl
    if a.longueur_km:
        vieux, neuf = struct.pack("<f", a.longueur_d_origine_km), struct.pack("<f", a.longueur_km)
        k = exp.find(vieux, debut + 8, fin)
        if k < 0 or exp.find(vieux, k + 4, fin) >= 0:
            sys.exit(f"longueur {a.longueur_d_origine_km} km introuvable ou trouvée plusieurs fois dans la ligne ; rien n'est écrit")
        exp[k:k + 4] = neuf
        bilan.append((f"{a.longueur_d_origine_km} km", f"{a.longueur_km} km", 1, 1))
    print(f"ligne {a.ligne} : octets {debut} à {fin} du .uexp ; " + " ; ".join(f"{v} -> {n} : {c} renvois" for v, n, c, _ in bilan))
    if not a.essai:
        f_exp.write_bytes(bytes(exp))
        print("écrit :", f_exp)


if __name__ == "__main__":
    main()
