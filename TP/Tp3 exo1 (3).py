# -*- coding: utf-8 -*-

def calculer_poids(chaine):
    voyelles = ['A', 'E', 'I', 'O', 'U', 'Y']
    poids = 0
    for i in range(len(chaine)):
        if chaine[i] in voyelles:
            poids += (i+1) * (voyelles.index(chaine[i]) * 4 + 1)
    return poids

chaine = str(input("Entrez une chaine de caractères : "))
poids = calculer_poids(chaine)
print("Le poids de la chaine {} est égal à {}".format(chaine, poids))
