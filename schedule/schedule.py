from flask import Flask, jsonify, make_response
import json
import requests

app = Flask(__name__)

PORT = 3202
HOST = '0.0.0.0'

with open('{}/databases/times.json'.format("."), "r") as jsf:
    schedule = json.load(jsf)["schedule"]


def write(schedule):
    with open("{}/databases/times.json".format("."), "w") as f:
        full = {}
        full["schedule"] = schedule
        json.dump(full, f)


@app.route("/", methods=['GET'])
def home():
    return "<h1 style='color:blue'>Welcome to the Showtime service!</h1>"


@app.route("/json", methods=["GET"])
def get_json():
    res = make_response(jsonify(schedule), 200)
    return res


@app.route("/dates/<date>", methods=["GET"])
def get_movies_by_date(date):
    # TODO : Aller chercher le nom du film à afficher plutôt que l'ID
    # Cherche la première entrée qui correspond à la date
    entry = next((
        d for d in schedule
        if str(d.get("date")) == str(date)
        ), None)

    if entry and "movies" in entry:
        return make_response(jsonify(entry["movies"]), 200)

    return make_response(jsonify({"error": "Date not found"}), 404)


@app.route("/movies/<movieid>", methods=["GET"])
def get_dates_by_movieid(movieid):
    # On teste si movieid est dans la liste 'movies' et on récupère la date
    dates = [
        m["date"]
        for m in schedule
        if "movies" in m and str(movieid) in [str(mid) for mid in m["movies"]]
    ]

    if dates:
        return make_response(jsonify(dates), 200)

    return make_response(jsonify({"error": "Movie not found"}), 404)


@app.route("/movies/<movieid>", methods=["DELETE"])
def del_movie_by_id(movieid):
    found = False

    for entry in schedule:
        # On filtre la liste pour retirer l'identifiant movieid
        initial_len = len(entry.get("movies", []))
        entry["movies"] = [
            mid for mid in entry.get("movies", [])
            if str(mid) != str(movieid)
            ]

        if len(entry["movies"]) < initial_len:
            found = True

    if found:
        write({"schedule": schedule})
        return make_response(jsonify(
            {"message": f"Movie {movieid} removed from all dates"}
            ), 200)

    return make_response(jsonify({"error": "Movie ID not found"}), 404)


@app.route("/dates/<date>", methods=["DELETE"])
def del_movies_by_date(date):
    entry = next((
        d for d in schedule
        if str(d.get("date")) == str(date)
        ), None)

    if entry:
        entry["movies"] = []
        write({"schedule": schedule})
        return make_response(jsonify(entry), 200)

    return make_response(jsonify({"error": "Date not found"}), 404)

@app.route("/dates/<date>", methods=["POST"])
def create_date(date):
    req = request.get_json()
    new_movies = req.get("movies", [])

    # On vérifie que les films existent bien dans movie
    for movie_id in new_movies:
        try:
            response = requests.get(f"http://127.0.0.1:3200/movies/{movie_id}")
        except requests.exceptions.RequestException:
            return make_response(jsonify({"error": "movie service unavailable"}), 503)
        if response.status_code != 200:
            return make_response(jsonify({"error": f"invalid movie: {movie_id}"}), 400)

    _schedule = next((d for d in schedule if str(d["date"]) == str(date)), None)

    # La date n'existe pas encore : on l'ajoute directement
    if _schedule is None:
        schedule.append({"date": str(date), "movies": list(new_movies)})
    else:
        # La date existe : vérifier que les films ne sont pas déjà programmés
        for movie_id in new_movies:
            if movie_id in _schedule["movies"]:
                return make_response(jsonify({"error": f"movie already booked for date: {date}"}), 409)
        _schedule["movies"].extend(new_movies)

    write(schedule)
    return make_response(jsonify({"message": "movie added"}), 201)

if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
