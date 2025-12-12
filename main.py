
# Interface graphique Tkinter qui utilise LibraryService
import tkinter as tk
from tkinter import ttk, messagebox

#importe les classes métier depuis src/__init__.py
from src import LibraryService, SubscriptionType, Role, CopyStatus


class LibraryApp(tk.Tk):
    #c'est la fenêtre principale de l'application

    def __init__(self):
        super().__init__()
        self.title("Bibliothèque - Gestion des utilisateurs & livres")
        self.geometry("900x550")

        #service métier (logique + persistance)
        self.lib = LibraryService()
        # sera rempli après connexion
        self.current_user = None

        #commence sur l'écran de connexion
        self.show_login()

    #gestion des "écrants" (frames)
    def clear(self):
        #supprime tous les widgets de la fenêtre -> c'est pour changer d'écran
        for w in self.winfo_children():
            w.destroy()

    def show_login(self):
        #sa affiche l'écran LoginFrame
        self.clear()
        frame = LoginFrame(self)
        frame.pack(fill="both", expand=True)

    def show_main(self):
        #sa affiche l'écran principal MainFrame
        self.clear()
        frame = MainFrame(self)
        frame.pack(fill="both", expand=True)


#frame de connexion / inscription
class LoginFrame(ttk.Frame):
    #formulaire pour se connecter / créer un compte

    def __init__(self, app: LibraryApp):
        super().__init__(app)
        self.app = app

        #variables Tkinter reliées aux champs de saisie
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.subscription_var = tk.StringVar(value=SubscriptionType.BASIC.value)
        self.is_admin_var = tk.BooleanVar(value=False)

        self.build()

    def build(self):
        #crée tous les widgets (labels, champs, boutons)."""
        title = ttk.Label(self, text="Bibliothèque", font=("Arial", 20, "bold"))
        title.pack(pady=20)

        frm = ttk.Frame(self)
        frm.pack(pady=10)

        #champ identifiant
        ttk.Label(frm, text="Nom d'utilisateur :").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(frm, textvariable=self.username_var).grid(row=0, column=1, padx=5, pady=5)

        #champ mot de passe
        ttk.Label(frm, text="Mot de passe :").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(frm, textvariable=self.password_var, show="*").grid(row=1, column=1, padx=5, pady=5)

        #le type d'abonnement (pour la création de compte)
        ttk.Label(frm, text="Abonnement (création) :").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        combo = ttk.Combobox(frm,textvariable=self.subscription_var,values=[s.value for s in SubscriptionType],state="readonly",width=12,)
        combo.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        #option compte admin
        ttk.Checkbutton(frm,text="Compte administrateur",variable=self.is_admin_var,).grid(row=3, column=1, sticky="w", padx=5, pady=5)

        #les boutons connexion / création
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="Se connecter", command=self.on_login).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Créer un compte", command=self.on_register).grid(row=0, column=1, padx=5)

    def on_login(self):
        #clic sur 'Se connecter'
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showerror("Erreur", "Veuillez saisir un nom d'utilisateur et un mot de passe.")
            return

        user = self.app.lib.authenticate(username, password)
        if not user:
            messagebox.showerror("Erreur", "Identifiants incorrects.")
            return

        #mémorise l'utilisateur connecté dans l'app
        self.app.current_user = user
        #ensuite sa affiche l'écran principal
        self.app.show_main()

    def on_register(self):
        #clic sur 'Créer un compte'
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()

        if not username or not password:
            messagebox.showerror("Erreur", "Veuillez saisir un nom d'utilisateur et un mot de passe")
            return

        try:
            sub_type = SubscriptionType(self.subscription_var.get())
        except ValueError:
            sub_type = SubscriptionType.BASIC

        try:
            user = self.app.lib.create_user(username=username,password=password,is_admin=self.is_admin_var.get(),subscription_type=sub_type,)
        except ValueError as e:
            messagebox.showerror("Erreur", str(e))
            return

        messagebox.showinfo("Succès",f"Compte créé pour '{user.username}'. Vous pouvez maintenant vous connecter")



#frame principale après connexion
class MainFrame(ttk.Frame):
    #contient les onglets : Catalogue / Mes emprunts / Administration

    def __init__(self, app: LibraryApp):
        super().__init__(app)
        self.app = app
        self.lib = app.lib
        self.user = app.current_user

        #c'est les listes gardent la correspondance index(listbox) -> objet
        self._books_list = []
        self._loans_list = []

        self.search_var = tk.StringVar()

        self.build()
        self.refresh_all()

    def build(self):
        #construit la barre du haut et les onglets
        #bandeau haut avec les infos de l'utilisateur
        info = ttk.Frame(self)
        info.pack(fill="x", padx=10, pady=5)

        self.user_label = ttk.Label(info, font=("Arial", 11, "bold"))
        self.user_label.pack(side="left")

        ttk.Button(info, text="Déconnexion", command=self.logout).pack(side="right", padx=5)

        #notebook = gestionnaire d'onglets
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        #onglet catalogue
        self.tab_catalog = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_catalog, text="Catalogue")
        self.build_catalog_tab()

        #onglet mes emprunts
        self.tab_loans = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_loans, text="Mes emprunts")
        self.build_loans_tab()

        #onglet admin ( si besoin )
        if self.user.role == Role.ADMIN:
            self.tab_admin = ttk.Frame(self.notebook)
            self.notebook.add(self.tab_admin, text="Administration")
            self.build_admin_tab()
        else:
            self.tab_admin = None


    #onglet Catalogue
    def build_catalog_tab(self):
        #crée les widgets de l'onglet 'Catalogue'
        top = ttk.Frame(self.tab_catalog)
        top.pack(fill="x", pady=5)

        ttk.Label(top, text="Recherche (titre/auteur) :").pack(side="left", padx=5)
        ttk.Entry(top, textvariable=self.search_var, width=30).pack(side="left", padx=5)
        ttk.Button(top, text="Rechercher", command=self.refresh_books).pack( side="left", padx=5)

        list_frame = ttk.Frame(self.tab_catalog)
        list_frame.pack(fill="both", expand=True, pady=5)


        #listbox pour afficher les livres
        self.books_listbox = tk.Listbox(list_frame, height=15)
        self.books_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.books_listbox.yview )
        scrollbar.pack(side="right", fill="y")
        self.books_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(self.tab_catalog)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Emprunter", command=self.borrow_selected_book).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Réserver", command=self.reserve_selected_book).grid(row=0, column=1, padx=5)

    def refresh_books(self):
        #recharge la liste de livres par rapport à la recherche
        query = self.search_var.get().strip()
        self._books_list = self.lib.search_books(query=query)

        self.books_listbox.delete(0, tk.END)
        for b in self._books_list:
            available = sum(1 for c in b.copies if c.status == CopyStatus.AVAILABLE)
            total = len(b.copies)
            avg = b.average_rating()
            txt = f"{b.title} - {b.author} [{b.category}]  ({available}/{total} dispo)"
            if avg is not None:
                txt += f"  ★ {avg:.1f}"
            self.books_listbox.insert(tk.END, txt)

    def _get_selected_book(self):
        #renvoie l'objet Book qui correspond à la ligne sélectionné
        try:
            idx = self.books_listbox.curselection()[0]
        except IndexError:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un livre.")
            return None
        return self._books_list[idx]

    def borrow_selected_book(self):
        #action du bouton 'Emprunter'
        book = self._get_selected_book()
        if not book:
            return
        try:
            loan = self.lib.borrow_book(self.user.id, book.id)
        except ValueError as e:
            messagebox.showerror("Impossible d'emprunter", str(e))
            return

        messagebox.showinfo("Emprunt réalisé",f"Vous avez emprunté '{book.title}' jusqu'au {loan.due_date}.",)
        self.refresh_all()

    def reserve_selected_book(self):
        #action du bouton 'Réserver'
        book = self._get_selected_book()
        if not book:
            return
        try:
            self.lib.reserve_book(self.user.id, book.id)
        except ValueError as e:
            messagebox.showerror("Réservation impossible", str(e))
            return

        messagebox.showinfo("Réservation enregistrée",f"Vous êtes maintenant en file d'attente pour '{book.title}'.",)
        self.refresh_all()

    #onglet Mes emprunt
    def build_loans_tab(self):
        #crée l'onglet 'Mes emprunts'
        list_frame = ttk.Frame(self.tab_loans)
        list_frame.pack(fill="both", expand=True, pady=5)

        self.loans_listbox = tk.Listbox(list_frame, height=12)
        self.loans_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.loans_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.loans_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(self.tab_loans)
        btn_frame.pack(pady=5)

        ttk.Button(btn_frame, text="Rendre le livre", command=self.return_selected_loan)\
            .grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Payer mes pénalités", command=self.pay_penalties)\
            .grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Actualiser", command=self.refresh_loans)\
            .grid(row=0, column=2, padx=5)

        #zone d'affichage des notifications (livres réservés dispo, etc...)
        notif_frame = ttk.LabelFrame(self.tab_loans, text="Notifications")
        notif_frame.pack(fill="x", padx=10, pady=10)

        self.notif_text = tk.Text(notif_frame, height=4, state="disabled")
        self.notif_text.pack(fill="x", padx=5, pady=5)

    def refresh_loans(self):
        #recharge la liste des emprunts actifs pour l'utilisateur connecté
        self._loans_list = self.lib.get_user_loans(self.user.id, active_only=True)

        self.loans_listbox.delete(0, tk.END)
        for l in self._loans_list:
            book = self.lib.store.state.books.get(l.book_id)
            title = book.title if book else "Livre inconnu"
            self.loans_listbox.insert(tk.END,f"{title}  | emprunté le {l.borrowed_at}  - retour prévu le {l.due_date}")

    def _get_selected_loan(self):
        #sa renvoie l'objet Loan qui est associé à la ligne sélectionnée
        try:
            idx = self.loans_listbox.curselection()[0]
        except IndexError:
            messagebox.showwarning("Attention", "Sélectionnez d'abord un emprunt.")
            return None
        return self._loans_list[idx]

    def return_selected_loan(self):
        #action du bouton 'Rendre le livre'
        loan = self._get_selected_loan()
        if not loan:
            return

        self.lib.return_book(loan.id)
        messagebox.showinfo("Retour enregistré", "Le livre a été rendu.")
        self.refresh_all()

    def pay_penalties(self):
        #action du bouton 'Payer mes pénalités' (simulation)
        user = self.lib.get_user(self.user.id)
        if user.penalties_due <= 0:
            messagebox.showinfo("Pénalités", "Vous n'avez aucune pénalité à payer.")
            return

        self.lib.pay_penalties(user.id)
        messagebox.showinfo("Pénalités", "Vos pénalités ont été marquées comme payées.")
        self.refresh_all()

    def refresh_notifications(self):
        #sa met à jour la zone de texte des notifications
        user = self.lib.get_user(self.user.id)

        self.notif_text.config(state="normal")
        self.notif_text.delete("1.0", tk.END)

        if not user.notifications:
            self.notif_text.insert(tk.END, "Aucune notification.\n")
        else:
            for msg in user.notifications:
                self.notif_text.insert(tk.END, f"• {msg}\n")

        self.notif_text.config(state="disabled")

    #onglet Administration
    def build_admin_tab(self):
        #crée l'onglet d'administration
        frm = ttk.Frame(self.tab_admin)
        frm.pack(fill="x", pady=10, padx=10)

        ttk.Label(frm, text="Titre :").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(frm, text="Auteur :").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(frm, text="Catégorie :").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(frm, text="Nb exemplaires :").grid(row=3, column=0, sticky="e", padx=5, pady=5)

        self.admin_title = tk.StringVar()
        self.admin_author = tk.StringVar()
        self.admin_category = tk.StringVar()
        self.admin_copies = tk.IntVar(value=1)

        ttk.Entry(frm, textvariable=self.admin_title, width=30)\
            .grid(row=0, column=1, padx=5, pady=5)
        ttk.Entry(frm, textvariable=self.admin_author, width=30)\
            .grid(row=1, column=1, padx=5, pady=5)
        ttk.Entry(frm, textvariable=self.admin_category, width=30)\
            .grid(row=2, column=1, padx=5, pady=5)
        ttk.Spinbox(frm, from_=1, to=20, textvariable=self.admin_copies, width=5)\
            .grid(row=3, column=1, sticky="w", padx=5, pady=5)

        ttk.Button(frm, text="Ajouter le livre", command=self.admin_add_book)\
            .grid(row=4, column=1, sticky="e", padx=5, pady=10)


        #widget Text qui vas afficher les statistiques
        self.stats_text = tk.Text(self.tab_admin, height=10, state="disabled")
        self.stats_text.pack(fill="both", expand=True, padx=10, pady=10)

    def admin_add_book(self):
        #action du bouton 'Ajouter le livre'
        title = self.admin_title.get().strip()
        author = self.admin_author.get().strip()
        category = self.admin_category.get().strip()
        copies = self.admin_copies.get()

        if not title or not author or not category:
            messagebox.showerror("Erreur", "Merci de remplir tous les champs.")
            return

        self.lib.add_book(title=title, author=author, category=category, copies=copies)
        messagebox.showinfo("Livre ajouté", f"'{title}' a été ajouté au catalogue.")
        #reset des champs
        self.admin_title.set("")
        self.admin_author.set("")
        self.admin_category.set("")
        self.admin_copies.set(1)
        self.refresh_all()

    def refresh_stats(self):
        #met à jour la zone de statistiques dans l'onglet admin
        if not self.tab_admin:
            return

        stats = self.lib.statistics()

        self.stats_text.config(state="normal")
        self.stats_text.delete("1.0", tk.END)

        self.stats_text.insert(tk.END,f"Taux d'occupation des exemplaires : {stats['occupation_rate']:.1f}%\n\n")

        self.stats_text.insert(tk.END, "Livres populaires :\n")
        for b in stats["popular_books"]:
            self.stats_text.insert(tk.END,f"  • {b['title']} ({b['author']}) - {b['loans']} emprunts\n",)

        self.stats_text.insert(tk.END, "\nUtilisateurs les plus actifs :\n")
        for u in stats["active_users"]:
            self.stats_text.insert(tk.END,f"  • {u['username']} - {u['loans']} emprunts\n",)

        self.stats_text.config(state="disabled")

    #fonctions utilitaires

    def refresh_all(self):
        #met à jour les infos de l'utilisateur, les listes, les notifications, les stats
        u = self.lib.get_user(self.user.id)
        self.user = u
        sub = u.subscription
        txt = (f"Connecté en tant que {u.username} "f"({u.role.value}, abo {sub.type.value}, exp. {sub.expires_at})"f" | Pénalités en cours : {u.penalties_due:.2f} €")
        self.user_label.config(text=txt)

        self.refresh_books()
        self.refresh_loans()
        self.refresh_notifications()
        self.refresh_stats()

    def logout(self):
        #déconnecte l'utilisateur et retourne à l'écran de login
        self.app.current_user = None
        self.app.show_login()


#le point d'entré du programme
if __name__ == "__main__":
    #c'est ce fichier lancé dans PyCharm (main.py)
    app = LibraryApp()
    app.mainloop()  #le démarrage de la boucle Tkinter
