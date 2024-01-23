from abc import ABC, abstractmethod

# Classe abstraite
class VehiculeUnmanned(ABC):
    @abstractmethod
    def executer_mission(self):
        pass

    @abstractmethod
    def status(self):
        pass

    @abstractmethod
    def santé(self):
        pass

    def demarrer(self):
        print("Démarrage du véhicule.")

# Classes de capacités spécifiques
class CapaciteSousMarine:
    def plonger(self):
        print("Plongée.")

class CapaciteAerienne:
    def voler(self):
        print("Vol.")

class CapaciteTerrestre:
    def rouler(self):
        print("Déplacement terrestre.")

# Sous-classes spécifiques
class UUV(VehiculeUnmanned, CapaciteSousMarine):
    def executer_mission(self):
        print("Exécution d'une mission sous-marine avec l'UUV.")
        self.plonger()

    def status(self):
        print("UUV prêt pour la mission.")

    def santé(self):
        print("New")

class UAV(VehiculeUnmanned, CapaciteAerienne):
    def executer_mission(self):
        print("Exécution d'une mission aérienne avec l'UAV.")
        self.voler()

    def status(self):
        print("UAV prêt pour la mission.")
    
    
    def santé(self):
        print("Ancien")

class UGV(VehiculeUnmanned, CapaciteTerrestre):
    def executer_mission(self):
        print("Exécution d'une mission terrestre avec l'UGV.")
        self.rouler()

    def status(self):
        print("UGV prêt pour la mission.")

    def santé(self):
        print("New")

# Exemple d'utilisation
uuv = UUV()
uuv.demarrer()
uuv.status()
uuv.santé()
uuv.executer_mission()

uav = UAV()
uav.demarrer()
uav.status()
uav.executer_mission()

ugv = UGV()
ugv.demarrer()
ugv.status()
ugv.executer_mission()
