import os
from flask import Flask, request, jsonify, make_response
import json
from flask_jwt_extended import (create_access_token, get_jwt_identity,
                                JWTManager, jwt_required)

app = Flask(__name__)

PORT = 3203
HOST = '0.0.0.0'

# Initialisation de la partie JWT
# Secret lu dans la variable d'environnement (fichier .env via
# docker-compose), avec une valeur par défaut pour le lancement hors Docker.
# Il est partagé avec les autres services, qui vérifient les tokens émis ici.
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret")
jwt = JWTManager(app)
# Le token est attendu dans le header Authorization (pas de cookie)
app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_COOKIE_SECURE"] = False

with open('{}/databases/users.json'.format("."), "r") as jsf:
    users = json.load(jsf)["users"]


def write(users):
    with open("{}/databases/users.json".format("."), "w") as f:
        full = {}
        full["users"] = users
        json.dump(full, f)


# Statut admin d'un utilisateur à partir de son nom (identité du token)
def is_admin(username):
    user = [user for user in users if user["name"] == username]
    if user:
        return (user[0]["admin"])
    return (False)


# Id d'un utilisateur à partir de son nom (identité du token)
def get_id(username):
    user = [user for user in users if user["name"] == username]
    if user:
        return (user[0]["id"])
    return (False)


# ===============================================================

# ROUTE de départ
@app.route("/", methods=['GET'])
def home():
    return "<h1 style='color:blue'>Welcome to the User service!</h1>"

# ==============================================================


# Route d'authentification
@app.route("/login", methods=['POST'])
def login():
    """
    Args:
        name (str, paramètre d'URL): nom de l'utilisateur.

    Returns:
        JSON : le token d'accès JWT, ou un message d'erreur.

    URLs à tester:
        POST localhost:PORT/login?name=<nom>
    """
    # On récupère le nom de l'utilisateur et on récupère son compte
    name = request.args.get("name")
    if not name:
        return make_response(jsonify({"error": "name required"}), 400)
    user = [user for user in users if user["name"] == name]
    if not user:
        return make_response(jsonify({"error": "user not found"}), 404)
    user = user[0]
    # On va créer un token avec le statut admin de l'utilisateur pour les
    # autres services qui n'ont pas accès à cette database.
    # L'id est ajouté aussi : booking compare l'id de l'URL à celui du token
    additionnal_claim = {"admin": user["admin"], "id": user["id"]}
    token = create_access_token(
        identity=name, additional_claims=additionnal_claim)
    return jsonify(access_token=token)


# Récupérer les infos de l'utilisateur du token
@app.route("/user_jwt/<username>", methods=["GET"])
# Même route sous le chemin utilisé dans le commit bf48c47
@app.route("/user/jwt/<username>", methods=["GET"])
@jwt_required()
def info(username):
    """
    Args:
        username (str): nom de l'utilisateur, doit être celui du token.

    Returns:
        JSON : les infos de l'utilisateur.

    URLs à tester:
        GET localhost:PORT/user_jwt/<username>
        GET localhost:PORT/user/jwt/<username>
        header : Authorization: Bearer <token>
    """
    current_user = get_jwt_identity()
    if current_user != username:
        return make_response(
            jsonify({"error": "Username and JWT mismatch"}), 400)
    for user in users:
        if current_user == str(user["name"]):
            return (make_response(jsonify(user), 200))
    return (make_response(jsonify({"error": "Not found"}), 404))


# ROUTE renvoi de toute la base (admin)
@app.route("/json", methods=["GET"])
@jwt_required()
def get_json():
    # Renvoie la liste des utilisateurs avec toutes les infos,
    # réservé aux admins
    current_user = get_jwt_identity()
    if not is_admin(current_user):
        return make_response(jsonify({"error": "forbidden"}), 403)
    res = make_response(jsonify(users), 200)
    return res


# Récupérer un utilisateur par son id (soi-même ou admin)
@app.route("/user/<user_id>", methods=["GET"])
@jwt_required()
def get_user_id(user_id):
    """
    Args:
        user_id (str): identifiant d'un utilisateur.

    Returns:
        JSON : l'utilisateur correspondant.

    URLs à tester:
        GET localhost:PORT/user/<user_id>
        header : Authorization: Bearer <token>
    """
    # Renvoie les infos d'un utilisateur,
    # réservé à l'utilisateur ou aux admins
    current_user = get_jwt_identity()
    if not (is_admin(current_user) or user_id == get_id(current_user)):
        return (make_response(jsonify({"error": "forbidden"}), 403))
    for user in users:
        if user_id == str(user["id"]):
            return (make_response(jsonify(user), 200))
    return (make_response(jsonify({"error": "Not found"}), 404))


# Récupérer la liste des admins (admin)
@app.route("/user/admin", methods=["GET"])
@jwt_required()
def get_admin():
    """
    Args:
        Aucun.

    Returns:
        JSON : la liste des utilisateurs admin.

    URLs à tester:
        GET localhost:PORT/user/admin
        header : Authorization: Bearer <token>
    """
    # Renvoie la liste des admins, réservé aux admins
    current_user = get_jwt_identity()
    if not is_admin(current_user):
        return (make_response(jsonify({"error": "forbidden"}), 403))
    rep = [user for user in users if user["admin"]]
    return (make_response(jsonify(rep), 200))


# Inscription ouverte sans token (jwt_required optionnel) ;
# seul un admin connecté peut créer un autre admin
@app.route("/user/<user_id>", methods=["POST"])
@jwt_required(optional=True)
def create_user(user_id):
    """
    Args:
        user_id (str): identifiant du nouvel utilisateur.

    Returns:
        JSON : l'utilisateur créé, ou un message d'erreur.

    URLs à tester:
        POST localhost:PORT/user/<user_id>
        header (optionnel, obligatoire pour créer un admin) : Authorization: Bearer <token>
        body : {"name": "<nom>", "last_active": <timestamp>, "admin": false}
    """
    # Créer un compte,
    # nécessite d'être admin pour créer un compte administrateur
    current_user = get_jwt_identity()
    for user in users:
        if user_id == str(user["id"]):
            # id déjà pris : 409 Conflict
            return (make_response(
                jsonify({"error": "user ID already exists"}), 409))
    # silent=True : pas de crash si le corps n'est pas du JSON
    req = request.get_json(silent=True) or {}
    if req.get("admin") and not is_admin(current_user):
        return (make_response(jsonify({"error": "forbidden"}), 403))
    # L'id de l'URL fait foi
    req["id"] = user_id
    users.append(req)
    write(users)
    return (make_response(jsonify(req), 201))


# Modifier un utilisateur (soi-même ou admin)
@app.route("/user/<user_id>", methods=["PUT"])
@jwt_required()
def modify_user(user_id):
    """
    Args:
        user_id (str): identifiant d'un utilisateur.

    Returns:
        JSON : l'utilisateur modifié, ou un message d'erreur.

    URLs à tester:
        PUT localhost:PORT/user/<user_id>
        header : Authorization: Bearer <token>
        body : {"name": "<nom>", "last_active": <timestamp>, "admin": false}
    """
    # Modifie un compte, réservé à l'utilisateur ou aux admins
    current_user = get_jwt_identity()
    if not (is_admin(current_user) or user_id == get_id(current_user)):
        return (make_response(jsonify({"error": "forbidden"}), 403))
    req = request.get_json(silent=True) or {}
    # Seul un admin peut donner le rôle admin (pas d'auto-promotion)
    if req.get("admin") and not is_admin(current_user):
        return (make_response(jsonify({"error": "forbidden"}), 403))
    for i in range(len(users)):
        if user_id == str(users[i]["id"]):
            users[i] = req
            users[i]["id"] = user_id
            write(users)
            return (make_response(jsonify(req), 200))
    return (make_response(jsonify({"error": "user not found"}), 404))


# Supprimer un utilisateur (soi-même ou admin)
@app.route("/user/<user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    """
    Args:
        user_id (str): identifiant d'un utilisateur.

    Returns:
        Réponse vide (204), ou un message d'erreur.

    URLs à tester:
        DELETE localhost:PORT/user/<user_id>
        header : Authorization: Bearer <token>
    """
    # Supprime un compte, réservé à l'utilisateur ou aux admins
    # (le token contient le nom : on le convertit en id avec get_id)
    current_user = get_jwt_identity()
    if not (is_admin(current_user) or user_id == get_id(current_user)):
        return (make_response(jsonify({"error": "forbidden"}), 403))
    for user in users:
        if user_id == str(user["id"]):
            users.remove(user)
            write(users)
            # 204 No Content : réponse vide
            return (make_response("", 204))
    return (make_response(jsonify({"error": "user not found"}), 404))


if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
