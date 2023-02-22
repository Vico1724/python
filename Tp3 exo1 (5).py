# -*- coding: utf-8 -*-

def deplacer(T, K):
    i = 0
    j = len(T) - 1
    while i < j:
        while T[i] < K:
            i += 1
        while T[j] >= K:
            j -= 1
        if i < j:
            T[i], T[j] = T[j], T[i]
    return T

# Exemple d'utilisation
T = [3, 5, 1, 6, 2, 7, 4]
K = 4
T = deplacer(T, K)
print(T)
