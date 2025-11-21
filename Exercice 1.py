#class mère
class Vehicule:
    def __init__(self, marque, modele):# --> met self sinon jpp mettre pour les fonctions après
        self.marque = marque # --> comme this en C# ou en Java
        self.modele = modele

    def afficher_info(self):
        print(f" Véhicule : {self.marque}, {self.modele}")# --> f-string est une chaîne formatée / {}  remplace par les valeurs

#class fille
class Voiture(Vehicule):# --> La parathèse pour l'Héritage
    def __init__(self, marque, modele, nombre_portes):
        super().__init__(marque, modele) # --> fonction super pour la class mère
        self.nombre_portes = nombre_portes

    def afficher_info(self):
        print(f"Voiture : {self.marque}, {self.modele}, {self.nombre_portes}")

#class fille
class Moto(Vehicule):
    def __init__(self, marque, modele, type_moteur):
        super().__init__(marque, modele)
        self.type_moteur = type_moteur

    def afficher_info(self):
        print(f"Moto : {self.marque}, {self.modele}, {self.type_moteur}")


V1 = Voiture (" Aventador SV", " Lamborghini", 3)
M1 = Moto (" Yamaha ", " MT-07", "689cc")

V1.afficher_info() # --> Appel de la fonciton afficher crée dans les class
M1.afficher_info()