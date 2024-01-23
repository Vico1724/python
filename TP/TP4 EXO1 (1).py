# -*- coding: utf-8 -*-
"""
Created on Wed Feb 22 13:45:34 2023

@author: Victor Orlando
"""

    
def est_palindrome(mot):
    if len(mot) <= 1:
        return True
    elif mot[0] != mot[-1]:
        return False
    else:
        return est_palindrome(mot[1:-1])
    
mot = input("Entrez un mot : ")

if est_palindrome(mot):
    print(f"{mot} est un palindrome.")
else:
    print(f"{mot} n'est pas un palindrome.")
