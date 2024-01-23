# -*- coding: utf-8 -*-
"""
Created on Wed Feb 22 14:07:45 2023

@author: Victor Orlando
"""

def maximum(tableau):
    if len(tableau) == 1:
        return tableau[0]
    else:
        max_du_reste = maximum(tableau[1:])
        return tableau[0] if tableau[0] > max_du_reste else max_du_reste
    
tableau = list(map(int, input("Entrez un tableau d'entiers séparés par des espaces : ").split()))


print(f"val max {maximum(tableau)}")

