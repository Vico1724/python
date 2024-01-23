# -*- coding: utf-8 -*-
"""
Created on Wed Feb 22 14:06:44 2023

@author: Victor Orlando
"""

def est_trie(tableau):
    if len(tableau) <= 1:
        return True
    elif tableau[0] > tableau[1]:
        return False
    else:
        return est_trie(tableau[1:])
    
tableau = list(map(int, input("Entrez un tableau d'entiers séparés par des espaces : ").split()))

if est_trie(tableau):
    print("Le tableau est trié par ordre croissant.")
else:
    print("Le tableau n'est pas trié par ordre croissant.")