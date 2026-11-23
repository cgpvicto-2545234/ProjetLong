import os
from flask import Flask, render_template, request
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Connexion à la base de données avec les informations du fichier .env
db = mysql.connector.connect(user=os.getenv("DB_USER"),
                             password=os.getenv("DB_PASSWORD"),
                             host=os.getenv("DB_HOST"),
                             port=int(os.getenv("DB_PORT")),
                             database=os.getenv("DB_NAME"))


# Page d'accueil : affiche le formulaire avec les choix provenant de la BD
@app.route('/')
def accueil():
    curseur = db.cursor(dictionary=True)

    curseur.execute("SELECT * FROM croutes")
    croutes = curseur.fetchall()

    curseur.execute("SELECT * FROM sauces")
    sauces = curseur.fetchall()

    curseur.execute("SELECT * FROM garnitures")
    garnitures = curseur.fetchall()

    curseur.close()
    return render_template("accueil.html", croutes=croutes, sauces=sauces, garnitures=garnitures)

# Résumé : affiche la commande SANS l'enregistrer dans la BD
@app.route('/resume', methods=['POST'])
def resume():
    nom = request.form['nom']
    telephone = request.form['telephone']
    adresse = request.form['adresse']
    id_croute = request.form['id_croute']
    id_sauce = request.form['id_sauce']
    ids_garnitures = request.form.getlist('garnitures')

    if nom == "" or telephone == "" or adresse == "":
        return render_template("erreur.html", erreur="Tous les champs du client sont obligatoires.")
    if len(ids_garnitures) > 4:
        return render_template("erreur.html", erreur="Vous pouvez choisir au maximum 4 garnitures.")

    curseur = db.cursor(dictionary=True)

    requete = "SELECT * FROM croutes WHERE id = %(id)s"
    curseur.execute(requete, {"id": id_croute})
    croute = curseur.fetchone()

    requete = "SELECT * FROM sauces WHERE id = %(id)s"
    curseur.execute(requete, {"id": id_sauce})
    sauce = curseur.fetchone()

    garnitures = []
    requete = "SELECT * FROM garnitures WHERE id = %(id)s"
    for id_garniture in ids_garnitures:
        curseur.execute(requete, {"id": id_garniture})
        garnitures.append(curseur.fetchone())

    curseur.close()

    if croute is None or sauce is None:
        return render_template("erreur.html", erreur="La croûte ou la sauce choisie n'existe pas.")

    client = {"nom": nom, "telephone": telephone, "adresse": adresse}
    return render_template("resume.html", client=client, croute=croute,
                           sauce=sauce, garnitures=garnitures)


# Confirmation : enregistre client, commande, pizza et garnitures
@app.route('/confirmer', methods=['POST'])
def confirmer():
    nom = request.form['nom']
    telephone = request.form['telephone']
    adresse = request.form['adresse']
    id_croute = request.form['id_croute']
    id_sauce = request.form['id_sauce']
    ids_garnitures = request.form.getlist('garnitures')

    if len(ids_garnitures) > 4:
        return render_template("erreur.html", erreur="Vous pouvez choisir au maximum 4 garnitures.")

    curseur = db.cursor()
    try:
        requete = """
        INSERT INTO clients (nom, telephone, adresse)
        VALUES (%(nom)s, %(telephone)s, %(adresse)s)
        """
        parametres = {"nom": nom, "telephone": telephone, "adresse": adresse}
        curseur.execute(requete, parametres)
        id_client = curseur.lastrowid

        requete = "INSERT INTO commandes (id_client) VALUES (%(id_client)s)"
        curseur.execute(requete, {"id_client": id_client})
        id_commande = curseur.lastrowid

        requete = """
        INSERT INTO pizza (id_commande, id_croute, id_sauce)
        VALUES (%(id_commande)s, %(id_croute)s, %(id_sauce)s)
        """
        parametres = {"id_commande": id_commande, "id_croute": id_croute, "id_sauce": id_sauce}
        curseur.execute(requete, parametres)
        id_pizza = curseur.lastrowid

        requete = """
        INSERT INTO pizza_garniture (id_pizza, id_garniture)
        VALUES (%(id_pizza)s, %(id_garniture)s)
        """
        for id_garniture in ids_garnitures:
            curseur.execute(requete, {"id_pizza": id_pizza, "id_garniture": id_garniture})

        db.commit()
        curseur.close()
        return render_template("confirmation.html", id_commande=id_commande)
    except mysql.connector.Error as erreur:
        db.rollback()
        return render_template("erreur.html", erreur=erreur.msg)


# Liste des commandes en attente de livraison
@app.route('/livraisons')
def livraisons():
    curseur = db.cursor(dictionary=True)
    requete = """
    SELECT co.id, co.date_commande, co.statut, cl.nom, cl.telephone, cl.adresse
    FROM livraisons_en_attente AS l
    JOIN commandes AS co ON co.id = l.id_commande
    JOIN clients AS cl ON cl.id = co.id_client
    ORDER BY l.date_ajout
    """
    curseur.execute(requete)
    commandes = curseur.fetchall()
    curseur.close()
    return render_template("livraisons.html", commandes=commandes)


# Compléter une livraison : statut = Livree et suppression de la commande de la table livraisons_en_attente
@app.route('/livrer/<int:id_commande>', methods=['POST'])
def livrer(id_commande):
    parametres = {"id_commande": id_commande}
    curseur = db.cursor()
    try:
        requete = "UPDATE commandes SET statut = 'Livree' WHERE id = %(id_commande)s"
        curseur.execute(requete, parametres)

        requete = "DELETE FROM livraisons_en_attente WHERE id_commande = %(id_commande)s"
        curseur.execute(requete, parametres)

        db.commit()
        curseur.close()
        return render_template("livraison_completee.html", id_commande=id_commande)
    except mysql.connector.Error as erreur:
        db.rollback()
        curseur.close()
        return render_template("erreur.html", erreur=erreur.msg)


if __name__ == '__main__':
    app.run(debug=True)