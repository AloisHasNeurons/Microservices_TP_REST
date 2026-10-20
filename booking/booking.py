from flask import Flask, render_template, request, jsonify, make_response
import json
from werkzeug.exceptions import NotFound
import requests

app = Flask(__name__)

PORT = 3201
HOST = '0.0.0.0'


# INITIALISATION

with open('{}/databases/bookings.json'.format("."), "r") as jsf:
   bookings = json.load(jsf)["bookings"]
   
def write(bookings):
    with open("{}/databases/bookings.json".format("."), "w") as f:
        full = {}
        full["bookings"] = bookings
        json.dump(full, f)

#===============================================================

# ROUTE de départ
@app.route("/", methods=['GET'])
def home():
   return "<h1 style='color:blue'>Welcome to the Booking service!</h1>"

# ROUTE renvoi de toute la base
@app.route("/json", methods=["GET"])
def get_json():
    res = make_response(jsonify(bookings), 200)
    return res

# ==============================================================

# Récupérer le Booking par userid
@app.route("/bookings/<userid>", methods=["GET"])
def get_movie_byid(userid):
    """
    Args:
        userid (id): identifiant d'un utilisateur.

    Returns:
        JSON : les entrées de bookings.json liées à userid.

    URLs à tester:
        GET loalhost/PORT/bookings/<userid>
    """
    
    for booking in bookings:
        if str(booking["userid"]) == str(userid):
            res = make_response(jsonify(booking), 200)
            return res
    return make_response(jsonify({"error": "User ID not found"}), 500)

# Récupère les détails des films par userid
@app.route("/bookings/details/<userid>", methods=["GET"])
def get_movies_detail_byid(userid):
    """
    Args:
        userid (id): identifiant d'un utilisateur.

    Returns:
        JSON : les entrées de bookings.json liées à userid.

    URLs à tester:
        GET loalhost/PORT/bookings/details/<userid>
    """

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
                        response = requests.get(f"http://127.0.0.1:3200/movies/{movie}")
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
def add_movie(userid):
    req = request.get_json()
    new_dates = req.get("dates", [])
    for entry in new_dates:
        entry["movies"] = to_list(entry["movies"])

    # On vérifie que les dates existe bien dans schedule
    for entry in new_dates:
        try:
            response = requests.get(f"http://127.0.0.1:3202/dates/{entry['date']}")
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
def del_movie(userid):
    for booking in bookings:
        if str(booking["userid"]) == str(userid):
            bookings.remove(booking)
            write(bookings)
            return make_response(jsonify(booking),200)

    res = make_response(jsonify({"error":"user ID not found"}),500)
    return res
 
@app.route("/bookings/<userid>/<date>", methods=['DELETE'])
def del_movie_by_date(userid,date):
    for booking in bookings:
        if str(booking["userid"]) == str(userid):
           for _date in booking["dates"]:
                if str(_date["date"]) == str(date):
                    booking["dates"].remove(_date)
                    write(bookings)
                    return make_response(jsonify(booking),200)
           return make_response(jsonify({"error":"date not found"}),501)

    res = make_response(jsonify({"error":"user ID not found"}),500)
    return res


if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   app.run(host=HOST, port=PORT)
