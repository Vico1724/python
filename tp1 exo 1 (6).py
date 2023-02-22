# -*- coding: utf-8 -*-
"""
Created on Mon Feb  6 15:42:40 2023

@author: vicoc
"""

def est_premier(n):
    if n < 2:
        return False
    for i in range(2, int(n**(0.5)) + 1):
        if n % i == 0:
            return False
    return True

def decomposer_en_premiers(n):
    premiers = []
    for i in range(2, n):
        if est_premier(i) and est_premier(n - i):
            premiers.append((i, n - i))
            break
    return premiers

n = int(input("Donner un nombre pair : "))
if n % 2 == 0:
    premiers = decomposer_en_premiers(n)
    if premiers:
        print("Le nombre {} est décomposable en deux nombres premiers : {} et {}".format(n, premiers[0][0], premiers[0][1]))
    else:
        print("Le nombre {} ne peut pas être décomposé en deux nombres premiers".format(n))
else:
    print("Le nombre donné n'est pas un nombre pair.")