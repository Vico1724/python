#!/usr/bin/env python
# -*- coding: utf-8 -*-

nombres = [5, 9, 12, 3, 7, 4, 2, 8, 6]

entiers_pairs = []
entiers_impairs = []

for nombre in nombres:
    if nombre % 2 == 0:
        entiers_pairs.append(nombre)
    else:
        entiers_impairs.append(nombre)

print("Liste des entiers pairs :", entiers_pairs)
print("Liste des entiers impairs :", entiers_impairs)
