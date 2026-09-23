from flask import Flask, render_template, request, jsonify, make_response
import json
from werkzeug.exceptions import NotFound

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
    # Cherche la première entrée qui correspond à la date
    entry = next((d for d in schedule if str(d.get("date")) == str(date)), None)

    if entry and "movies" in entry:
        return make_response(jsonify(entry["movies"]), 200)

    return make_response(jsonify({"error": "Date not found"}), 404)


if __name__ == "__main__":
    print("Server running in port %s" % (PORT))
    app.run(host=HOST, port=PORT)
