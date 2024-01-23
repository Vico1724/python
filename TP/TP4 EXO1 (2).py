# -*- coding: utf-8 -*-
"""
Created on Wed Feb 22 13:49:51 2023

@author: Victor Orlando
"""

def trouver_position(tableau, valeur):
    """
    Cherche la position d'une valeur dans un tableau.
    Retourne la position de la valeur s'il est trouvé, -1 sinon.
    """
    for i in range(len(tableau)):
        if tableau[i] == valeur:
            return i
    return -1

def changer_valeur_composante_connexe(tableau, position, valeur):
    """
    Propage une valeur x à toutes les valeur 1 de la composante connexe
    à partir de la position donnée.
    """
    if not (0 <= position < len(tableau) and tableau[position] == 1):
        return
    
    tableau[position] = valeur
    
    for voisin in (position-1, position+1, position-len(tableau), position+len(tableau)):
        changer_valeur_composante_connexe(tableau, voisin, valeur)

# Exemple d'utilisation
tableau = [0, 1, 1, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 0, 1]
composante_connexe = 2

position = trouver_position(tableau, 1)

while position != -1:
    changer_valeur_composante_connexe(tableau, position, composante_connexe)
    composante_connexe += 1
    position = trouver_position(tableau, 1)

# Affichage du résultat
print(tableau)