# -*- coding: utf-8 -*-
"""
Created on Mon Feb  6 15:42:57 2023

@author: vicoc
"""

def est_premier(n):
    if n < 2:
        return False
    for i in range(2, int(n**(0.5)) + 1):
        if n % i == 0:
            return False
    return True

def somme_chiffres(n):
    return sum([int(i) for i in str(n)])

# Détermination si un nombre est premier
n = int(input("Entrer un nombre : "))
if est_premier(n):
    print("Le nombre {} est premier".format(n))
else:
    print("Le nombre {} n'est pas premier".format(n))

# Affichage de tous les nombres premiers inférieurs ou égaux à 50
print("Les nombres premiers inférieurs ou égaux à 50 sont :")
for i in range(2, 51):
    if est_premier(i):
        print(i)

# Affichage de tous les nombres <1000 qui sont premiers et dont la somme de leurs chiffres est supérieure à 5
print("Les nombres premiers inférieurs à 1000 et dont la somme de leurs chiffres est supérieure à 5 sont :")
for i in range(2, 1000):
    if est_premier(i) and somme_chiffres(i) > 5:
        print(i)