
import os
from datetime import date, timedelta

from src import LibraryService, DataStore, SubscriptionType  #importe la logique métier

#chemin vers un fichier de données dédié aux tests
TEST_DB_PATH = "data/test_data.json"


def setup_function(_):
    #réinitialise un fichier de test propre avant chaque test
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


def test_user_cannot_borrow_with_penalties():
#fonction spéciale reconnue par pytest. Elle est appelée AVANT CHAQUE test du fichier
#ici, sert pour supprimer le fichier data de test,pour que chaque test reparte d'une base propre

    #crée un DataStore qui va utiliser data/test_data.json
    store = DataStore(TEST_DB_PATH)
    #crée un service métier qui utilise ce DataStore de test
    lib = LibraryService(store)


    user = lib.create_user("bob", "1234", subscription_type=SubscriptionType.BASIC)  #création d'un utilisateur "bob"
    book = lib.add_book("Livre test", "Auteur", "catégorie", copies=1)  #ajout d'un livre avec 1 exemplaire

    loan = lib.borrow_book(user.id, book.id)

    #simule un retour en retard de 5 jours
    loan.due_date = date.today() - timedelta(days=5)
    lib.return_book(loan.id)

    #vérifie que l'utilisateur a bien des pénalités
    assert lib.get_user(user.id).penalties_due > 0

    #un nouvel emprunt doit échouer
    raised = False
    try:
        lib.borrow_book(user.id, book.id)
    except ValueError:
        raised = True

    assert raised is True  #le test échou si raised est False
