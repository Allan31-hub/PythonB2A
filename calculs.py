# src/calculs.py

from __future__ import annotations #permet d'utiliser des types qui ne sont définis qu'après

from dataclasses import dataclass, field  #classe "automatique" pour stocker des données
from datetime import datetime, date, timedelta
from enum import Enum  #Enum = liste de valeurs prédéfinies
from typing import List, Dict, Optional
import json
import os
import uuid #uuid = identifiant unique généré automatiquement



#Énumérations et constantes
#Role utilisateur -> admin ou simple utilisateur
class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"


class CopyStatus(str, Enum):
    AVAILABLE = "available" #disponible
    LOANED = "loaned"  #emprunté
    DAMAGED = "damaged" #endommagé
    LOST = "lost"  #perdu


class SubscriptionType(str, Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    VIP = "vip"


#Limites par type d’abonnement
#on y retrouve : nb max de livres empruntés en même temps / durée de l'emprunt en jours / pénalité par jour de retard / nb d'emprunts max par mois
SUBSCRIPTION_CONFIG: Dict[SubscriptionType, Dict[str, object]] = {
    SubscriptionType.BASIC: { "max_active_loans": 1,"loan_days": 14,"penalty_per_day": 0.50,"monthly_loan_cap": 5},
    SubscriptionType.PREMIUM: { "max_active_loans": 3, "loan_days": 21,"penalty_per_day": 0.25, "monthly_loan_cap": 10},
    SubscriptionType.VIP: { "max_active_loans": 5, "loan_days": 28, "penalty_per_day": 0.0, "monthly_loan_cap": 999}}



#Modèles de données
@dataclass
class Subscription:
    type: SubscriptionType
    expires_at: date

    @property
    def config(self) -> Dict[str, object]:
        return SUBSCRIPTION_CONFIG[self.type]

    def to_dict(self) -> Dict[str, object]:
        return {
            "type": self.type.value,
            "expires_at": self.expires_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: Dict[str, object]) -> "Subscription":
        return Subscription(
            type=SubscriptionType(data["type"]),
            expires_at=date.fromisoformat(data["expires_at"]),  # type: ignore[arg-type]
        )


@dataclass
class User:
    id: str #identifiant unique
    username: str
    password: str
    role: Role = Role.USER
    subscription: Subscription = field(
        default_factory=lambda: Subscription( SubscriptionType.BASIC, date(2099, 1, 1), ))
    penalties_due: float = 0.0   #pénalités impayées
    monthly_loan_counter: int = 0  #nb d'emprunts ce mois-ci
    monthly_counter_year_month: str = field( default_factory=lambda: datetime.now().strftime("%Y-%m") ) # exemple :"2025-11"
    notifications: List[str] = field(default_factory=list)


    def is_admin(self) -> bool:
        return self.role == Role.ADMIN


    #Gestion du compteur mensuel
    def _refresh_month_counter_if_needed(self) -> None:
        current_ym = datetime.now().strftime("%Y-%m")
        if self.monthly_counter_year_month != current_ym:
            self.monthly_counter_year_month = current_ym
            self.monthly_loan_counter = 0

    def can_borrow(self, active_loans_count: int) -> bool:

        #Vérifie si l'utilisateur peut emprunter :
        #- pas de pénalités impayées
        #- abonnement non expiré
        #- limite d'emprunts simultanés
        #- limite mensuelle

        self._refresh_month_counter_if_needed()

        #pénalités -> emprunt interdit
        if self.penalties_due > 0:
            return False

        #abonnement expiré -> emprunt interdit
        if self.subscription.expires_at < date.today():
            return False

        cfg = self.subscription.config


        #trop d'emprunts en même temps
        if active_loans_count >= cfg["max_active_loans"]:
            return False

        #trop d'emprunts ce mois-ci
        if self.monthly_loan_counter >= cfg["monthly_loan_cap"]:
            return False

        return True


    def register_new_loan(self) -> None:
        self._refresh_month_counter_if_needed()
        self.monthly_loan_counter += 1


    #Sérialisation JSON
    def to_dict(self) -> Dict[str, object]:
        return { "id": self.id,"username": self.username,"password": self.password,"role": self.role.value,"subscription": self.subscription.to_dict(),"penalties_due": self.penalties_due,"monthly_loan_counter": self.monthly_loan_counter,"monthly_counter_year_month": self.monthly_counter_year_month,"notifications": self.notifications,}


    @staticmethod
    def from_dict(data: Dict[str, object]) -> "User":
        return User(
            id=data["id"],  # type: ignore[index]
            username=data["username"],  # type: ignore[index]
            password=data["password"],  # type: ignore[index]
            role=Role(data.get("role", "user")),  # type: ignore[arg-type]
            subscription=Subscription.from_dict(data["subscription"]),  # type: ignore[index]
            penalties_due=float(data.get("penalties_due", 0.0)),
            monthly_loan_counter=int(data.get("monthly_loan_counter", 0)),
            monthly_counter_year_month=str(
                data.get("monthly_counter_year_month", datetime.now().strftime("%Y-%m"))
            ),
            notifications=list(data.get("notifications", [])),  # type: ignore[list-item]
        )


@dataclass
class BookCopy:
    id: str
    status: CopyStatus = CopyStatus.AVAILABLE

    def to_dict(self) -> Dict[str, object]:
        return {"id": self.id, "status": self.status.value}

    @staticmethod
    def from_dict(data: Dict[str, object]) -> "BookCopy":
        return BookCopy( id=data["id"],status=CopyStatus(data.get("status", "available")))


@dataclass
class Book:
    id: str
    title: str
    author: str
    category: str
    copies: List[BookCopy] = field(default_factory=list)  #liste d'exemplaires
    ratings: List[int] = field(default_factory=list)   #notes 1 à 5
    comments: List[Dict[str, str]] = field(default_factory=list)  #commentaires
    loan_history: List[str] = field(default_factory=list)  #liste d'id d'emprunts


    def available_copy(self) -> Optional[BookCopy]:
        return next((c for c in self.copies if c.status == CopyStatus.AVAILABLE), None) #Renvoie un exemplaire disponible, ou None si il n'y en a plus.


    def average_rating(self) -> Optional[float]:
        if not self.ratings:
            return None
        return sum(self.ratings) / len(self.ratings)


    def to_dict(self) -> Dict[str, object]:
        return { "id": self.id,"title": self.title,"author": self.author,"category": self.category,"copies": [c.to_dict() for c in self.copies],"ratings": self.ratings,"comments": self.comments,"loan_history": self.loan_history,}

    @staticmethod
    def from_dict(data: Dict[str, object]) -> "Book":
        return Book(
            id=data["id"],  # type: ignore[index]
            title=data["title"],  # type: ignore[index]
            author=data["author"],  # type: ignore[index]
            category=data["category"],  # type: ignore[index]
            copies=[BookCopy.from_dict(c) for c in data.get("copies", [])],  # type: ignore[list-item]
            ratings=list(data.get("ratings", [])),  # type: ignore[list-item]
            comments=list(data.get("comments", [])),  # type: ignore[list-item]
            loan_history=list(data.get("loan_history", [])),  # type: ignore[list-item]
        )


@dataclass
class Loan:
    #Emprunt d'un exemplaire par un utilisateur.
    id: str
    user_id: str
    book_id: str
    copy_id: str
    borrowed_at: date
    due_date: date
    returned_at: Optional[date] = None #En gros None veut dire que ce n'est pas encore rendu
    penalty_applied: float = 0.0  #pénalité calculée à la fin

    @property
    def is_active(self) -> bool:
        return self.returned_at is None

    def to_dict(self) -> Dict[str, object]:
        return { "id": self.id,"user_id": self.user_id,"book_id": self.book_id,"copy_id": self.copy_id,"borrowed_at": self.borrowed_at.isoformat(),"due_date": self.due_date.isoformat(),"returned_at": self.returned_at.isoformat() if self.returned_at else None,"penalty_applied": self.penalty_applied,}


    @staticmethod
    def from_dict(data: Dict[str, object]) -> "Loan":
        return Loan(
            id=data["id"],  # type: ignore[index]
            user_id=data["user_id"],  # type: ignore[index]
            book_id=data["book_id"],  # type: ignore[index]
            copy_id=data["copy_id"],  # type: ignore[index]
            borrowed_at=date.fromisoformat(data["borrowed_at"]),  # type: ignore[arg-type]
            due_date=date.fromisoformat(data["due_date"]),  # type: ignore[arg-type]
            returned_at=(
                date.fromisoformat(data["returned_at"])  # type: ignore[arg-type]
                if data.get("returned_at")
                else None
            ),
            penalty_applied=float(data.get("penalty_applied", 0.0)))


@dataclass
class Reservation:
    id: str
    user_id: str
    book_id: str
    created_at: datetime
    notified: bool = False

    def to_dict(self) -> Dict[str, object]:
        return { "id": self.id,"user_id": self.user_id,"book_id": self.book_id,"created_at": self.created_at.isoformat(),"notified": self.notified,}

    @staticmethod
    def from_dict(data: Dict[str, object]) -> "Reservation":
        return Reservation(
            id=data["id"],  # type: ignore[index]
            user_id=data["user_id"],  # type: ignore[index]
            book_id=data["book_id"],  # type: ignore[index]
            created_at=datetime.fromisoformat(data["created_at"]),  # type: ignore[arg-type]
            notified=bool(data.get("notified", False)))



@dataclass
class LibraryState:
    users: Dict[str, User] = field(default_factory=dict)
    books: Dict[str, Book] = field(default_factory=dict)
    loans: Dict[str, Loan] = field(default_factory=dict)
    reservations: Dict[str, Reservation] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {"users": {uid: u.to_dict() for uid, u in self.users.items()},"books": {bid: b.to_dict() for bid, b in self.books.items()},"loans": {lid: l.to_dict() for lid, l in self.loans.items()},"reservations": {rid: r.to_dict() for rid, r in self.reservations.items()}}



    @staticmethod
    def from_dict(data: Dict[str, object]) -> "LibraryState":
        state = LibraryState()
        state.users = {
            uid: User.from_dict(u)  # type: ignore[arg-type]
            for uid, u in data.get("users", {}).items()  # type: ignore[union-attr]
        }
        state.books = {
            bid: Book.from_dict(b)  # type: ignore[arg-type]
            for bid, b in data.get("books", {}).items()  # type: ignore[union-attr]
        }
        state.loans = {
            lid: Loan.from_dict(l)  # type: ignore[arg-type]
            for lid, l in data.get("loans", {}).items()  # type: ignore[union-attr]
        }
        state.reservations = {
            rid: Reservation.from_dict(r)  # type: ignore[arg-type]
            for rid, r in data.get("reservations", {}).items()  # type: ignore[union-attr]
        }
        return state



#Persistance JSON
#Gèrel'état de la bibliothèquedans data/data.json.
class DataStore:

    def __init__(self, path: str = "data/data.json"):
        self.path = path
        self.state = LibraryState() #état initial vide
        self.load()   #essaie de charger depuis le disque

    def load(self) -> None:

        #si le fichier n'existe pas on crée le dossier + un fichier vide
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            self.save()
            return

        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        #reconstruit LibraryState depuis le dict JSON
        self.state = LibraryState.from_dict(raw)

    def save(self) -> None:

        #Sauvegarde l'état courant dans le JSON
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.state.to_dict(), f, indent=2, ensure_ascii=False)



#Service principal
class LibraryService:

    def __init__(self, store: Optional[DataStore] = None):
        self.store = store or DataStore()


    #Utilisateurs
    def create_user( self,username: str,password: str,is_admin: bool = False,subscription_type: SubscriptionType = SubscriptionType.BASIC,subscription_duration_days: int = 365):

        #interdit les doublons de username
        if any(u.username == username for u in self.store.state.users.values()):
            raise ValueError("Nom d'utilisateur déjà pris")

        user_id = str(uuid.uuid4())  #identifiant unique aléatoire
        subscription = Subscription( type=subscription_type,expires_at=date.today() + timedelta(days=subscription_duration_days))
        role = Role.ADMIN if is_admin else Role.USER

        user = User(id=user_id,username=username,password=password,role=role,subscription=subscription,)

        self.store.state.users[user_id] = user
        self.store.save()
        return user


    def authenticate(self, username: str, password: str) -> Optional[User]:
        #Retourne l'utilisateur si login/mdp corrects, sinon None
        for user in self.store.state.users.values():
            if user.username == username and user.password == password:
                return user
        return None

    def get_user(self, user_id: str) -> User:
        #Raccourci pour récupérer un utilisateur par son id
        return self.store.state.users[user_id]


    def get_user_loans(self, user_id: str, active_only: bool = False) -> List[Loan]:
        loans = [l for l in self.store.state.loans.values() if l.user_id == user_id]
        if active_only:
            loans = [l for l in loans if l.is_active]
        loans.sort(key=lambda l: l.borrowed_at, reverse=True)
        return loans


    def get_user_reservations(self, user_id: str) -> List[Reservation]:

        #liste les réservations d'un utilisateur, triées par date de création
        res = [
            r for r in self.store.state.reservations.values()
            if r.user_id == user_id
        ]
        res.sort(key=lambda r: r.created_at)
        return res


    def change_subscription(self,user_id: str,new_type: SubscriptionType,extra_days: int = 365) -> None:

        user = self.get_user(user_id)
        today = date.today()
        base = max(user.subscription.expires_at, today)
        user.subscription.type = new_type
        user.subscription.expires_at = base + timedelta(days=extra_days)
        self.store.save()

    #livres et exemplaires
    def add_book( self,title: str,author: str,category: str,copies: int = 1) -> Book:

        book_id = str(uuid.uuid4())
        book = Book( id=book_id,title=title,author=author,category=category,copies=[BookCopy(id=str(uuid.uuid4())) for _ in range(copies)],)

        self.store.state.books[book_id] = book
        self.store.save()
        return book

    def remove_book(self, book_id: str) -> None:
        #interdit si emprunts actifs
        for loan in self.store.state.loans.values():
            if loan.book_id == book_id and loan.is_active:
                raise ValueError()
            #impossible de supprimer un livre avec des emprunts actifs



        #on supprime le livre
        self.store.state.books.pop(book_id, None)

        #supprimer aussi les réservations associées
        to_delete = [
            rid
            for rid, r in self.store.state.reservations.items()
            if r.book_id == book_id
        ]
        for rid in to_delete:
            del self.store.state.reservations[rid]

        self.store.save()


    def add_copies(self, book_id: str, count: int) -> None:
        book = self.store.state.books[book_id]
        for _ in range(count):
            book.copies.append(BookCopy(id=str(uuid.uuid4())))
        self.store.save()


    def set_copy_status(self,book_id: str,copy_id: str,status: CopyStatus) -> None:
        #change le statut d'un exemplaire (disponible, perdu, endommagé...)
        book = self.store.state.books[book_id]
        for copy in book.copies:
            if copy.id == copy_id:
                copy.status = status
                break
        self.store.save()

    def search_books(self,query: str = "",category: Optional[str] = None,author: Optional[str] = None) -> List[Book]:
        q = query.lower()
        result: List[Book] = []

        for book in self.store.state.books.values():
            if q and q not in book.title.lower() and q not in book.author.lower():
                continue
            if category and book.category.lower() != category.lower():
                continue
            if author and book.author.lower() != author.lower():
                continue
            result.append(book)
        return result


    def book_history(self, book_id: str) -> List[Loan]:
        #renvoie l'historique d'emprunt complet pour un livre
        book = self.store.state.books[book_id]
        return [self.store.state.loans[lid] for lid in book.loan_history]


    #Emprunts
    def _active_loans_for_user(self, user_id: str) -> List[Loan]:
        #récupère les emprunts encore actifs d'un user
        return [
            l for l in self.store.state.loans.values()
            if l.user_id == user_id and l.is_active
        ]

    def borrow_book(self, user_id: str, book_id: str) -> Loan:
                #Tente d'emprunter un livre :
                #vérifie que l'utilisateur respecte les règles
                #choisit un exemplaire disponible
                #crée un Loan

        user = self.get_user(user_id)
        book = self.store.state.books[book_id]
        active_loans = self._active_loans_for_user(user_id)

        if not user.can_borrow(len(active_loans)):
            raise ValueError("L'utilisateur ne peut pas emprunter de livre ","(limite atteinte, abonnement expiré ou pénalités impayées)")

        copy = book.available_copy()
        if not copy:
            raise ValueError("Aucun exemplaire disponible, vous pouvez seulement réserver ce livre")


        cfg = user.subscription.config
        loan_id = str(uuid.uuid4())
        borrowed_at = date.today()
        due_date = borrowed_at + timedelta(days=int(cfg["loan_days"]))

        loan = Loan(id=loan_id,user_id=user_id,book_id=book_id,copy_id=copy.id,borrowed_at=borrowed_at,due_date=due_date)

        #marque l'exemplaire comme emprunté
        copy.status = CopyStatus.LOANED
        #ajoute l'emprunt à l'historique du livre
        book.loan_history.append(loan_id)
        #met à jour le compteur mensuel de l'utilisateur
        user.register_new_loan()
        #on enregistre l'emprunt dans l'état
        self.store.state.loans[loan_id] = loan
        self.store.save()
        return loan


    def return_book(self, loan_id: str) -> None:
               #enregistre le retour d'un livre :
               #remet l'exemplaire en disponible
               #calcule les pénalités de retard
               #notifie la prochaine réservation
        loan = self.store.state.loans[loan_id]
        if not loan.is_active:
            return #déjà rendu on fait rien


        loan.returned_at = date.today()
        user = self.get_user(loan.user_id)
        book = self.store.state.books[loan.book_id]

        # Exemplaire re-disponible
        #recherche l'exemplaire correspondant et on le remet dispo
        for copy in book.copies:
            if copy.id == loan.copy_id:
                copy.status = CopyStatus.AVAILABLE
                break


        #calcul des pénalités
        cfg = user.subscription.config
        penalty_rate = float(cfg["penalty_per_day"])

        if loan.returned_at > loan.due_date and penalty_rate > 0:
            days_late = (loan.returned_at - loan.due_date).days
            penalty = days_late * penalty_rate
            loan.penalty_applied = penalty
            user.penalties_due += penalty


    #réservations
    def reserve_book(self, user_id: str, book_id: str) -> Reservation:
        book = self.store.state.books[book_id]



        #ne réserve que s'il n'y a plus d'exemplaire disponible
        if book.available_copy():
            raise ValueError("Au moins un exemplaire est disponible, inutile de réserver")


        #pas de double réservation pour le même livre et le même user
        for r in self.store.state.reservations.values():
            if r.user_id == user_id and r.book_id == book_id:
                raise ValueError("Vous avez déjà une réservation pour ce livre")

        res_id = str(uuid.uuid4())
        res = Reservation( id=res_id,user_id=user_id,book_id=book_id,created_at=datetime.now(),)
        self.store.state.reservations[res_id] = res
        self.store.save()
        return res

    def cancel_reservation(self, reservation_id: str) -> None:
        #annule purement une réservation
        self.store.state.reservations.pop(reservation_id, None)
        self.store.save()


    #notifie la plus ancienne réservation non encore notifiée
    def _notify_next_reservation(self, book_id: str) -> None:

        reservations = [
            r for r in self.store.state.reservations.values()
            if r.book_id == book_id and not r.notified
        ]

        if not reservations:
            return

        reservations.sort(key=lambda r: r.created_at)
        next_res = reservations[0]

        user = self.get_user(next_res.user_id)
        msg = f"Le livre réservé '{self.store.state.books[book_id].title}'est maintenant disponible"
        user.notifications.append(msg)
        next_res.notified = True


    #avis et recommandations
    def rate_book( self,user_id: str,book_id: str,rating: int,comment: str = "") -> None:
        if rating < 1 or rating > 5:
            raise ValueError("La note doit être entre 1 et 5")

        book = self.store.state.books[book_id]


        #vérifie que l'utilisateur a déjà emprunté ce livre
        if not any(
            l.user_id == user_id and l.book_id == book_id
            for l in self.store.state.loans.values()):

            raise ValueError("Vous devez avoir emprunté le livre pour le noter")

        book.ratings.append(rating)
        if comment:
            book.comments.append({"user_id": user_id, "text": comment})

        self.store.save()


    def get_book_reviews(self, book_id: str) -> List[Dict[str, str]]:
        return self.store.state.books[book_id].comments


    def popular_books(self, limit: int = 5) -> List[Book]:
        books = list(self.store.state.books.values())
        books.sort(key=lambda b: len(b.loan_history), reverse=True)
        return books[:limit]


    #Statistiques admin
    def statistics(self) -> Dict[str, object]:
        #sa retourne quelques statistiques globales :
        #en gros c'est le taux d'occupation des exemplaires
        #c'est le top 5 des livres les plus empruntés
        #autre top 5 mais des utilisateurs les plus actifs

        total_copies = sum(len(b.copies) for b in self.store.state.books.values())
        active_loans = [
            l for l in self.store.state.loans.values()
            if l.is_active
        ]

        occupied_copies = len(active_loans)
        occupation_rate = ((occupied_copies / total_copies) * 100 if total_copies else 0.0)

        popular = [{"book_id": b.id,"title": b.title,"author": b.author,"loans": len(b.loan_history)}
            for b in self.store.state.books.values()]


        popular.sort(key=lambda x: x["loans"], reverse=True)
        popular = popular[:5]

        user_counts: Dict[str, int] = {}
        for l in self.store.state.loans.values():
            user_counts[l.user_id] = user_counts.get(l.user_id, 0) + 1

        active_users = sorted(
            ({"user_id": uid, "username": self.store.state.users[uid].username,"loans": count
                }for uid, count in user_counts.items()),key=lambda x: x["loans"],reverse=True,)[:5]

        return {"occupation_rate": occupation_rate,"popular_books": popular,"active_users": active_users}

#__all__ permet de contrôler se qui est importer par "from src import *
__all__ = ["Role", "CopyStatus", "SubscriptionType", "Subscription", "User", "BookCopy","Book","Loan","Reservation","LibraryState","DataStore","LibraryService"]
