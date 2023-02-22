# -*- coding: utf-8 -*-
"""
Created on Mon Feb  6 13:51:05 2023

@author: vicoc
"""

# Exercice 2
# Demander à l'utilisateur de saisir une chaîne de caractères
chaine = input("Saisir une chaîne de caractères :")

# Afficher le nombre de mots de la chaîne
mots = chaine.split()
print("Nombre de mots :", len(mots))

# Afficher le nombre d’occurrences de la lettre « o »
print("Nombre d'occurrences de la lettre 'o' :", chaine.count("o"))

# Renverser l’ordre des mots
chaine_inverse = " ".join(mots[::-1])
print("Chaine renversée :", chaine_inverse)

# Remplacer le mot « bonjour » par « bienvenue »
chaine_remplacee = chaine.replace("bonjour", "bienvenue")
print("Chaine remplacée :", chaine_remplacee)