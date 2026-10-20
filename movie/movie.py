import os
from functools import wraps
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, jwt_required
import json

# import sys
from flask import Flask, jsonify, make_response, request
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3200
HOST = "0.0.0.0"

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


with open("{}/databases/movies.json".format("."), "r") as jsf:
    movies = json.load(jsf)["movies"]
    print(movies)


def write(movies):
    with open("{}/databases/movies.json".format("."), "w") as f:
        full = {}
        full["movies"] = movies
        json.dump(full, f)


# ===============================================================

# ROUTE de départ
@app.route("/", methods=["GET"])
def home():
    return make_response(
        "<h1 style='color:blue'>Welcome to the Movie service!</h1>", 200
    )


# ROUTE renvoi de toute la base
@app.route("/json", methods=["GET"])
# Lecture : tout utilisateur connecté
@jwt_required()
def get_json():
    res = make_response(jsonify(movies), 200)
    return res

# ==============================================================


# Récupérer un film par son id
@app.route("/movies/<movieid>", methods=["GET"])
# Lecture : tout utilisateur connecté
@jwt_required()
def get_movie_byid(movieid):
    """
    Args:
        movieid (str): identifiant d'un film.

    Returns:
        JSON : le film correspondant à movieid.

    URLs à tester:
        GET localhost:PORT/movies/<movieid>
        header : Authorization: Bearer <token>
    """
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            res = make_response(jsonify(movie), 200)
            return res
    return make_response(jsonify({"error": "Movie ID not found"}), 500)


# Récupérer un film par son titre
@app.route("/moviesbytitle", methods=["GET"])
# Lecture : tout utilisateur connecté
@jwt_required()
def get_movie_bytitle():
    """
    Args:
        title (str, paramètre d'URL): titre exact du film.

    Returns:
        JSON : le film correspondant au titre.

    URLs à tester:
        GET localhost:PORT/moviesbytitle?title=<title>
        header : Authorization: Bearer <token>
    """
    json = ""
    if request.args:
        req = request.args
        for movie in movies:
            if str(movie["title"]) == str(req["title"]):
                json = movie

    if not json:
        res = make_response(jsonify({"error": "movie title not found"}), 500)
    else:
        res = make_response(jsonify(json), 200)
    return res


# Ajouter un film (admin)
@app.route("/movies/<movieid>", methods=["POST"])
# Réservé aux admins
@admin_required
def add_movie(movieid):
    """
    Args:
        movieid (str): identifiant du nouveau film.

    Returns:
        JSON : Message de confirmation ou d'erreur.

    URLs à tester:
        POST localhost:PORT/movies/<movieid>
        header : Authorization: Bearer <token>
        body : {"id": "<movieid>", "title": "<titre>", "director": "<réalisateur>", "rating": <note>}
    """
    req = request.get_json()
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            print(movie["id"])
            print(movieid)
            return make_response(jsonify({"error": "movie ID already exists"}), 500)

    movies.append(req)
    write(movies)
    res = make_response(jsonify({"message": "movie added"}), 201)
    return res


# Modifier la note d'un film (admin)
@app.route("/movies/<movieid>/<rate>", methods=['PUT'])
# Réservé aux admins
@admin_required
def update_movie_rating(movieid, rate):
    """
    Args:
        movieid (str): identifiant d'un film.
        rate (str): nouvelle note du film.

    Returns:
        JSON : le film avec sa nouvelle note.

    URLs à tester:
        PUT localhost:PORT/movies/<movieid>/<rate>
        header : Authorization: Bearer <token>
    """
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            movie["rating"] = rate
            res = make_response(jsonify(movie),200)
            write(movies)
            return res

    res = make_response(jsonify({"error": "movie ID not found"}), 500)
    return res


# Supprimer un film (admin)
@app.route("/movies/<movieid>", methods=['DELETE'])
# Réservé aux admins
@admin_required
def del_movie(movieid):
    """
    Args:
        movieid (str): identifiant d'un film.

    Returns:
        JSON : le film supprimé.

    URLs à tester:
        DELETE localhost:PORT/movies/<movieid>
        header : Authorization: Bearer <token>
    """
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            movies.remove(movie)
            write(movies)
            return make_response(jsonify(movie),200)

    res = make_response(jsonify({"error": "movie ID not found"}), 500)
    return res


if __name__ == "__main__":
    # p = sys.argv[1]
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
