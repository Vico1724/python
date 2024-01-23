# -*- coding: utf-8 -*-

# Création des instances de voiture
volkswagen_golf = {'marque': 'Volkswagen', 'modele': 'Golf', 'matricule': 'AB-123-CD', 'couleur': 'rouge', 'chevaux': 7}
renault_clio = {'marque': 'Renault', 'modele': 'Clio', 'matricule': 'FM-528-WC', 'couleur': 'noir', 'chevaux': 4}
peugeot_407 = {'marque': 'Peugeot', 'modele': '407', 'matricule': 'AB-428-WC', 'couleur': 'blanc', 'chevaux': 6}
volkswagen_polo = {'marque': 'Volkswagen', 'modele': 'Polo', 'matricule': 'GD-060-YQ', 'couleur': 'gris', 'chevaux': 5}

# Stockage des instances dans une liste
voitures = [volkswagen_golf, renault_clio, peugeot_407, volkswagen_polo]

# Affichage des voitures ayant une puissance supérieure ou égale à 5
print("Voitures ayant une puissance supérieure ou égale à 5 :")
for voiture in voitures:
    if voiture['chevaux'] >= 5:
        print(voiture)

# Demande à l'utilisateur de saisir une marque de voiture et affichage des voitures correspondantes
while True:
    marque = str(input("Veuillez saisir une marque de voiture : ")).lower()
    voitures_marque = [voiture for voiture in voitures if voiture['marque'].lower() == marque]
    if len(voitures_marque) > 0:
        print("Voitures de la marque " + marque + " :")
        for voiture in voitures_marque:
            print(voiture)
        break
    else:
        print("Aucune voiture de la marque " + marque + " n'a été trouvée. Veuillez réessayer.")

# Modification de la couleur des voitures rouges en vert
for voiture in voitures:
    if voiture['couleur'] == 'rouge':
        voiture['couleur'] = 'vert'

# Affichage des voitures après la modification de couleur
print("Voitures après la modification de couleur :")
for voiture in voitures:
    print(voiture)
