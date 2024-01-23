#!/usr/bin/env python
# -*- coding: utf-8 -*-

# demande à l'utilisateur de saisir une chaîne de caractères
texte = str(input("Veuillez saisir une chaîne de caractères : "))

# crée un dictionnaire vide pour stocker les fréquences des mots
freq_mots = {}

# divise la chaîne de caractères en mots individuels
mots = texte.split()

# boucle sur tous les mots pour calculer leur fréquence
for mot in mots:
    if mot in freq_mots:
        freq_mots[mot] += 1
    else:
        freq_mots[mot] = 1

# affiche le dictionnaire contenant les fréquences de tous les mots
print(freq_mots)
