import os
from functools import wraps
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, jwt_required
from flask import Flask, render_template, request, jsonify, make_response
import json
from werkzeug.exceptions import NotFound
import requests

app = Flask(__name__)

PORT = 3201
HOST = '0.0.0.0'


# INITIALISATION
# Vérification des tokens JWT émis par le service user :
# ce service n'en crée pas, il vérifie seulement leur signature
# avec le même secret (variable d'environnement JWT_SECRET_KEY,
# même valeur par défaut que le service user hors Docker)
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret")
jwt = JWTManager(app)


# Décorateur : token valide obligatoire ET claim "admin" à True,
# sinon 401 (pas de token / token invalide) ou 403 (pas admin)
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if not get_jwt().get("admin", False):
            return make_response(jsonify({"error": "forbidden"}), 403)
        return fn(*args, **kwargs)
    return wrapper


# Vrai si le token appartient à userid, ou si c'est un admin
# (l'identité du token est le nom : on compare avec le claim "id")
def is_self_or_admin(userid):
    return get_jwt().get("admin", False) or str(get_jwt().get("id")) == str(userid)


# URLs des autres services : localhost par défaut (lancement hors Docker),
# noms des services docker-compose sinon (voir docker-compose.yml)
MOVIE_URL = os.environ.get("MOVIE_URL", "http://127.0.0.1:3200")
SCHEDULE_URL = os.environ.get("SCHEDULE_URL", "http://127.0.0.1:3202")


# movie et schedule exigent un token : on transmet celui de l'appelant
def auth_header():
    return {"Authorization": request.headers.get("Authorization", "")}


with open('{}/databases/bookings.json'.format("."), "r") as jsf:
    bookings = json.load(jsf)["bookings"]


def write(bookings):
    with open("{}/databases/bookings.json".format("."), "w") as f:
        full = {}
        full["bookings"] = bookings
        json.dump(full, f)


# ===============================================================


# ROUTE de départ
@app.route("/", methods=['GET'])
def home():
    return "<h1 style='color:blue'>Welcome to the Booking service!</h1>"


# ROUTE renvoi de toute la base
@app.route("/json", methods=["GET"])
# Toutes les réservations : réservé aux admins
@admin_required
def get_json():
    res = make_response(jsonify(bookings), 200)
    return res


# ==============================================================


# Récupérer le Booking par userid
@app.route("/bookings/<userid>", methods=["GET"])
@jwt_required()
def get_movie_byid(userid):
    """
    Args:
        userid (id): identifiant d'un utilisateur.

    Returns:
        JSON : les entrées de bookings.json liées à userid.

    URLs à tester:
        GET loalhost/PORT/bookings/<userid>
    """

    # Chacun ne gère que ses propres réservations (sauf admin)
    if not is_self_or_admin(userid):
        return make_response(jsonify({"error": "forbidden"}), 403)
    for booking in bookings:
        if str(booking["userid"]) == str(userid):
            res = make_response(jsonify(booking), 200)
            return res
    return make_response(jsonify({"error": "User ID not found"}), 500)


# Récupère les détails des films par userid
@app.route("/bookings/details/<userid>", methods=["GET"])
@jwt_required()
def get_movies_detail_byid(userid):
    """
    Args:
        userid (id): identifiant d'un utilisateur.

    Returns:
        JSON : les entrées de bookings.json liées à userid.

    URLs à tester:
        GET loalhost/PORT/bookings/details/<userid>
    """
    # Chacun ne gère que ses propres réservations (sauf admin)
    if not is_self_or_admin(userid):
        return make_response(jsonify({"error": "forbidden"}), 403)

    for booking in bookings:
        if str(booking["userid"]) == str(userid):
            # Copie pour ne pas remplacer les identifiants dans la base
            res = dict(booking)
            res["dates"] = []
            for d in booking["dates"]:
                movies = to_list(d["movies"])
                movies_detail = []
                for movie in movies:
                    try:
                        response = requests.get(
                            # URL configurable + token transmis
                            f"{MOVIE_URL}/movies/{movie}", headers=auth_header())
                    except requests.exceptions.RequestException:
                        return make_response(jsonify({"error": "movie service unavailable"}), 503)
                    if response.status_code != 200:
                        return make_response(jsonify({"error": f"invalid movie: {movie}"}), 400)
                    movies_detail.append(response.json())
                res["dates"].append({"date": d["date"], "movies": movies_detail})
            return make_response(jsonify(res), 200)
    return make_response(jsonify({"error": "User ID not found"}), 500)


# Petite fonction métier
def to_list(value):
    return value if isinstance(value, list) else [value]


# Ajoute une ou plusieurs dates à la réservation d'un utilisateur
@app.route("/bookings/<userid>", methods=["POST"])
@jwt_required()
def add_movie(userid):
    """
        Args:
            userid (str): identifiant d'un utilisateur.

        Returns:
            JSON : Message de confirmation ou d'erreur.

        URLs à tester:
            POST localhost:PORT/bookings/<userid>
            body : {"userid": "<userid>", "dates": [{"date": "<date>", "movies": "<movie_id>"}]}
        """
    # Chacun ne gère que ses propres réservations (sauf admin)
    if not is_self_or_admin(userid):
        return make_response(jsonify({"error": "forbidden"}), 403)
    req = request.get_json()
    new_dates = req.get("dates", [])
    for entry in new_dates:
        entry["movies"] = to_list(entry["movies"])

    # On vérifie que les dates existe bien dans schedule
    for entry in new_dates:
        try:
            response = requests.get(
                # URL configurable + token transmis
                f"{SCHEDULE_URL}/dates/{entry['date']}", headers=auth_header())
        except requests.exceptions.RequestException:
            return make_response(jsonify({"error": "schedule service unavailable"}), 503)
        if response.status_code != 200:
            return make_response(jsonify({"error": f"invalid date: {entry['date']}"}), 400)

    booking = next((b for b in bookings if str(b["userid"]) == str(userid)), None)

    # L'utilisateur a-t-il déjà une réservation ?
    if booking is None:
        # NON : on ajoute tout de suite
        bookings.append({"userid": userid, "dates": new_dates})
    else:
        # SI la date existe : Vérifier si la date contient le film.
        for entry in new_dates:
            existing = next((d for d in booking["dates"] if str(d["date"]) == str(entry["date"])), None)
            if existing is None:
                booking["dates"].append(entry)
            else:
                deja_reserves = [m for m in entry["movies"] if m in existing["movies"]]
                if deja_reserves:
                    return make_response(jsonify({"error": f"movie already booked for date: {entry['date']}"}), 409)
                existing["movies"].extend(entry["movies"])

    write(bookings)
    return make_response(jsonify({"message": "movie added"}), 201)


@app.route("/bookings/<userid>", methods=['DELETE'])
@jwt_required()
def del_movie(userid):
    # Chacun ne gère que ses propres réservations (sauf admin)
    if not is_self_or_admin(userid):
        return make_response(jsonify({"error": "forbidden"}), 403)
    for booking in bookings:
        if str(booking["userid"]) == str(userid):
            bookings.remove(booking)
            write(bookings)
            return make_response(jsonify(booking),200)

    res = make_response(jsonify({"error":"user ID not found"}),500)
    return res


@app.route("/bookings/<userid>/<date>", methods=['DELETE'])
@jwt_required()
def del_movie_by_date(userid, date):
    # Chacun ne gère que ses propres réservations (sauf admin)
    if not is_self_or_admin(userid):
        return make_response(jsonify({"error": "forbidden"}), 403)
    for booking in bookings:
        if str(booking["userid"]) == str(userid):
            for _date in booking["dates"]:
                if str(_date["date"]) == str(date):
                    booking["dates"].remove(_date)
                    write(bookings)
                    return make_response(jsonify(booking), 200)
            return make_response(jsonify({"error": "date not found"}), 501)

    res = make_response(jsonify({"error": "user ID not found"}), 500)
    return res


if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
