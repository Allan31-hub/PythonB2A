import json
import csv

class Livre:
    def __init__(self, titre, auteur, annee):
        self.titre = titre
        self.auteur = auteur
        self.annee = annee

    def to_dict(self):
        return { "titre": self.titre,"auteur": self.auteur,"annee": self.annee }

    staticmethod
    def from_dict(data):
        return Livre( titre=data.get("titre", ""), auteur=data.get("auteur", ""), annee=data.get("annee", "") )




class Bibliotheque:
    def __init__(self):
        self.catalogue = [] # liste de Livre

    def ajouter_livre(self, livre):
        self.catalogue.append(livre)




    # ---------- Sauvegarde / chargement JSON ----------

    def sauvegarder_json(self, chemin_fichier):
        data = [livre.to_dict() for livre in self.catalogue]

        try: # --> ( gère les erreurs ) Anticiper un problème potentiel et d'exécuter du code
             # alternatif en cas d'erreur afin d'éviter que le programme ne plante
            with open(chemin_fichier, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(" Sauvegarde JSON réussie.")

        except PermissionError:    # --> sert à gérer les erreurs (exceptions) en Python
            print(" Erreur : permissions insuffisantes pour écrire dans ce fichier.")
        except OSError as e:
            print(" Erreur système lors de la sauvegarde :", e)




    def charger_json(self, chemin_fichier):
        try:
            with open(chemin_fichier, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.catalogue = [Livre.from_dict(item) for item in data]
            print(" Chargement JSON réussi.")

        except FileNotFoundError:
            print(" Erreur : fichier JSON inexistant.")
        except json.JSONDecodeError:
            print(" Erreur : format JSON invalide.")
        except PermissionError:
            print(" Erreur : permissions insuffisantes pour lire ce fichier.")
        except OSError as e:
            print(" Erreur système lors du chargement :", e)




    # ---------- Export CSV ----------

    def exporter_csv(self, chemin_fichier):
        try:
            with open(chemin_fichier, "w", newline="", encoding="utf-8") as f:
                champs = ["titre", "auteur", "annee"]
                writer = csv.DictWriter(f, fieldnames=champs, delimiter=';')
                writer.writeheader()

                for livre in self.catalogue:
                    writer.writerow(livre.to_dict())

            print(" Export CSV réussi.")

        except PermissionError:
            print(" Erreur : permissions insuffisantes pour écrire dans ce fichier CSV.")
        except OSError as e:
            print(" Erreur système lors de l'export CSV :", e)





# ---------- Programme principal (test) ----------

if __name__ == "__main__":
    biblio = Bibliotheque()

    # Ajout de quelques livres pour tester
    biblio.ajouter_livre(Livre("1984", "George Orwell", 1949))
    biblio.ajouter_livre(Livre("Fondation", "Isaac Asimov", 1951))

    # Sauvegarde en JSON
    biblio.sauvegarder_json("catalogue.json")

    # Export CSV
    biblio.exporter_csv("catalogue.csv")

    # Test de chargement
    biblio.catalogue = []          # on vide
    biblio.charger_json("catalogue.json")

    # Affichage du contenu rechargé
    for livre in biblio.catalogue:
        print(f"{livre.titre} - {livre.auteur} ({livre.annee})")
