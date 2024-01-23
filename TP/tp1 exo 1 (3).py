# -*- coding: utf-8 -*-
"""
Created on Mon Feb  6 14:01:52 2023

@author: vicoc
"""

# Exercice 3
# Capital initial
capital = 1000.0

# Taux d'intérêts
taux = 1.10

# Calculer le capital pour les trois premières années
for i in range(3):
  capital *= taux
  print("Année {} : {:.3f}".format(i + 1, capital))