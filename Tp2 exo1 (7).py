#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Définition de la liste de nombres
liste = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

# Calcul de la somme des éléments de la liste
somme = sum(liste)
print("La somme des éléments de la liste est :", somme)

# Multiplication de tous les éléments de la liste
produit = 1
for element in liste:
    produit *= element
print("Le produit des éléments de la liste est :", produit)

# Suppression des éléments dupliqués de la liste
liste_sans_doublons = list(set(liste))
print("Liste sans doublons :", liste_sans_doublons)

# Comparaison de deux listes
liste1 = [1, 2, 3, 4, 5]
liste2 = [4, 5, 6, 7, 8]
commun = False
for element in liste1:
    if element in liste2:
        commun = True
        break
if commun:
    print("Les deux listes ont une valeur commune.")
else:
    print("Les deux listes n'ont pas de valeur commune.")
