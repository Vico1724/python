# Exercice 1
# Demander à l'utilisateur de saisir son nom
nom = input("Saisir votre nom :\n").upper()

# Demander à l'utilisateur de saisir son prénom
prenom = input("Saisir votre prénom :\n").upper()

# Afficher son code formé par les deux premières lettres de son nom et la dernière lettre de son prénom
code = nom[:2] + prenom[-1]
print("Votre Code :", code)

# Afficher son mot de passe formé les deux deuxièmes moitiés, respectivement, du nom et du prénom renversées, répétées 3 fois.
mot_de_passe = (nom[len(nom)//2:] + prenom[:len(prenom)//2])[::-1] * 3
print("Votre mot de passe :", mot_de_passe)