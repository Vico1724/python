# -*- coding: utf-8 -*-
ch = input("Saisir une chaine de caractères : ")

# 1. Tester si la chaine commence par une majuscule et se termine par un point
if ch[0].isupper() and ch[-1] == '.':
    print("La chaine respecte la convention.")
else:
    ch = ch.capitalize() + '.'
    print("La chaine a été modifiée : {}".format(ch))

# 2. Afficher pour chaque mot l'intervalle de chaine allant de la lettre de code minimal à la lettre de code maximal
for mot in ch.split():
    debut = min(mot)
    fin = max(mot)
    intervalle = ch[ch.index(debut):ch.index(fin) + 1]
    print("Intervalle pour {} : {}".format(mot, intervalle))

# 3. Trier les mots par ordre croissant de la 1ère lettre
mots_tries = sorted(ch.split(), key=lambda mot: mot[0])
ch_triee = ' '.join(mots_tries)
print("Chaine triée par ordre croissant de la 1ère lettre : {}".format(ch_triee))

# 4. Trier les mots par longueur décroissante
mots_tries = sorted(ch.split(), key=lambda mot: len(mot), reverse=True)
ch_triee = ' '.join(mots_tries)
print("Chaine triée par longueur décroissante : {}".format(ch_triee))
