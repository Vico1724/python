# -*- coding: utf-8 -*-
mois = int(input("Saisir un mois (1-12) : "))

# Vérification du nombre de jours dans le mois
if mois in [1, 3, 5, 7, 8, 10, 12]:
    nb_jours = 31
elif mois == 2:
    nb_jours = 28
else:
    nb_jours = 30

# Demande du jour de la date
jour = int(input("Saisir un jour (1-{}): ".format(nb_jours)))
while jour < 1 or jour > nb_jours:
    jour = int(input("Jour invalide. Saisir un jour (1-{}): ".format(nb_jours)))

# Demande de l'année de la date
annee = int(input("Saisir une année (4 chiffres) : "))

# Affichage de la date au format demandé
print("{:02d}/{:02d}/{}".format(jour, mois, annee))
