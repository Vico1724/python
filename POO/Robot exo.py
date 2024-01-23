from PIL import Image

class Saiyan:
    def __init__(self, nom):
        self.nom = nom
        self.niveau = 0  # Niveaux étendus

    def transformer(self, niveau_souhaite):
        if niveau_souhaite <= 5 and niveau_souhaite >= 0:  # Exemple : 0 à 5 pour les niveaux
            self.niveau = niveau_souhaite
            print(f"{self.nom} se transforme en Super Saiyan niveau {self.niveau}!")
        else:
            print("Niveau de transformation non valide.")

    def afficher_transformation(self):
        transformations = {
            0: "Normal",
            1: "Super Saiyan (Jaune clair)",
            2: "Super Saiyan 2 (Jaune)",
            3: "Super Saiyan 3 (Jaune long)",
            4: "Super Saiyan God (Rouge)",
            5: "Super Saiyan Blue (Bleu)"
        }
        print(f"{self.nom} - {transformations.get(self.niveau, 'Inconnu')}")



def afficher_pixel_art(niveau):
    couleurs = {
        0: (0, 0, 0),       # Noir
        1: (255, 255, 0),   # Jaune clair
        2: (255, 223, 0),   # Jaune
        3: (255, 223, 0),   # Jaune long
        4: (255, 0, 0),     # Rouge
        5: (0, 0, 255)      # Bleu
    }

    taille = 10  # Taille d'un côté du pixel art en pixels
    image = Image.new("RGB", (taille, taille), couleurs[niveau])
    image.show()

# Exemple d'utilisation
goku = Saiyan("Goku")
niveau_transformation = int(input("Entrez le niveau de transformation (0-5): "))
goku.transformer(niveau_transformation)
goku.afficher_transformation()
afficher_pixel_art(goku.niveau)

