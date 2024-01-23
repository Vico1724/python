# -*- coding: utf-8 -*-

# Exercice 6.1
liste1 = [i+3 for i in range(6)]
print(liste1)

# Exercice 6.2
liste2 = [i+3 for i in range(6) if i >= 2]
print(liste2)

# Exercice 6.3
chaine1 = "abc"
chaine2 = "de"
liste3 = [a+b for a in chaine1 for b in chaine2]
print(liste3)
