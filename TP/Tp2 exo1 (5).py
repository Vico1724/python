# -*- coding: utf-8 -*-

# Définition de la liste
liste = [17, 38, 10, 25, 72]

# Tri et affichage de la liste
liste.sort()
print(liste)

# Ajout de l'élément 12 à la liste et affichage
liste.append(12)
print(liste)

# Renversement et affichage de la liste
liste.reverse()
print(liste)

# Affichage de l'indice de l'élément 17
print(liste.index(17))

# Affichage de la sous-liste du 2e au 3e élément
print(liste[1:3])

# Affichage de la sous-liste du début au 2e élément
print(liste[:2])

# Affichage de la sous-liste du 3e élément à la fin de la liste
print(liste[2:])

# Affichage de la sous-liste complète de la liste
print(liste[:])

# Affichage du dernier élément en utilisant un indiçage négatif
print(liste[-1])
