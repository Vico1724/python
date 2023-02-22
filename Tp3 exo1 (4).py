# -*- coding: utf-8 -*-

import numpy as np

def eststochastique(P):
    return np.allclose(P.sum(axis=1), 1) and np.all(P >= 0)

def estbistochastique(P):
    return eststochastique(P) and np.allclose(P.sum(axis=0), 1)

def vecteurstable(G, h):
    return np.allclose(G @ h, h) and np.sum(h) == 1

# Exemple d'utilisation
P = np.array([[0.1, 0.2, 0.7], [0.3, 0.3, 0.4], [0.5, 0.1, 0.4]])
h = np.array([0.3, 0.3, 0.4])
print("La matrice P est stochastique :", eststochastique(P))
print("La matrice P est bistochastique :", estbistochastique(P))
print("Le vecteur h est stable pour la matrice G :", vecteurstable(P, h))
