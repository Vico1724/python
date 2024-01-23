#!/usr/bin/env python
# -*- coding: utf-8 -*-

def eststochastique(P):
    n = len(P)
    m = len(P[0])
    for i in range(n):
        row_sum = sum(P[i])
        if abs(row_sum - 1) > 1e-8:
            return False
        for j in range(m):
            if P[i][j] < 0 or P[i][j] > 1:
                return False
    return True

def estbistochastique(P):
    n = len(P)
    m = len(P[0])
    for i in range(n):
        row_sum = sum(P[i])
        if abs(row_sum - 1) > 1e-8:
            return False
        for j in range(m):
            if P[i][j] < 0 or P[i][j] > 1:
                return False
    for j in range(m):
        col_sum = sum([P[i][j] for i in range(n)])
        if abs(col_sum - 1) > 1e-8:
            return False
    return True

def vecteurstable(G, h):
    n = len(G)
    m = len(G[0])
    for i in range(n):
        sum = 0
        for j in range(m):
            sum += G[i][j] * h[j]
        if abs(sum - h[i]) > 1e-8:
            return False
    if abs(sum(h) - 1) > 1e-8:
        return False
    return True

# Exemple d'utilisation
P = [[0.1, 0.2, 0.7], [0.3, 0.3, 0.4], [0.5, 0.1, 0.4]]
h = [0.3, 0.3, 0.4]
print("La matrice P est stochastique :", eststochastique(P))
print("La matrice P est bistochastique :", estbistochastique(P))
print("Le vecteur h est stable pour la matrice G :", vecteurstable(P, h))
