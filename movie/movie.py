import json

# import sys
from flask import Flask, jsonify, make_response, request
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3200
HOST = "0.0.0.0"

current_user = {
      "id": "chris_rivers",
      "name": "Chris Rivers",
      "last_active":1360031010,
      "admin": True
}

with open("{}/databases/movies.json".format("."), "r") as jsf:
    movies = json.load(jsf)["movies"]
    print(movies)


def write(movies):
    with open("{}/databases/movies.json".format("."), "w") as f:
        full = {}
        full["movies"] = movies
        json.dump(full, f)


# root message
@app.route("/", methods=["GET"])
def home():
    return make_response(
        "<h1 style='color:blue'>Welcome to the Movie service!</h1>", 200
    )


@app.route("/json", methods=["GET"])
def get_json():
    res = make_response(jsonify(movies), 200)
    return res


@app.route("/movies/<movieid>", methods=["GET"])
def get_movie_byid(movieid):
    for movie in movies:
        if str(movie["id"]) == str(movieid):
            res = make_response(jsonify(movie), 200)
            return res
    return make_response(jsonify({"error": "Movie ID not found"}), 500)


@app.route("/moviesbytitle", methods=["GET"])
def get_movie_bytitle():
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


@app.route("/movies/<movieid>", methods=["POST"])
def add_movie(movieid):
    if not current_user["admin"]:
        make_response(jsonify({"error" : "forbidden"}), 403)
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


if __name__ == "__main__":
    # p = sys.argv[1]
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
