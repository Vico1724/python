# -*- coding: utf-8 -*-
"""
Created on Mon Feb  6 15:01:44 2023

@author: vicoc
"""

A = int(input("Saisir A: "))
B = int(input("Saisir B: "))

perimeter = 2 * (A + B)
area = A * B
is_square = A == B
diameter = ((A**2) + (B**2))**0.5

print("Périmètre:", perimeter)
print("Surface:", area)
print("Carré:", is_square)
print("Diamètre:", format(diameter, ".2f"))

R = int(input("Saisir R: "))
volume = 3.14 * (R**2) * A
print("Volume:", volume)