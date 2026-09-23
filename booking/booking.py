from flask import Flask, render_template, request, jsonify, make_response
import json
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3201
HOST = '0.0.0.0'

with open('{}/databases/bookings.json'.format("."), "r") as jsf:
   bookings = json.load(jsf)["bookings"]
   
def write(bookings):
    with open("{}/databases/bookings.json".format("."), "w") as f:
        full = {}
        full["bookings"] = bookings
        json.dump(full, f)


@app.route("/", methods=['GET'])
def home():
   return "<h1 style='color:blue'>Welcome to the Booking service!</h1>"

@app.route("/json", methods=["GET"])
def get_json():
    res = make_response(jsonify(bookings), 200)
    return res


@app.route("/bookings/<userid>", methods=["GET"])
def get_movie_byid(userid):
    for booking in bookings:
        if str(booking["userid"]) == str(userid):
            res = make_response(jsonify(booking), 200)
            return res
    return make_response(jsonify({"error": "User ID not found"}), 500)
 
@app.route("/bookings/<userid>", methods=["POST"])
def add_movie(userid):
    req = request.get_json()

    for booking in bookings:
        if str(booking["userid"]) == str(userid):
            print(booking["userid"])
            print(userid)
            for _date in req["dates"]:
                  if str(_date) in [d for d in booking["dates"]]:
                      res = make_response(jsonify({"error": "date already exists"}), 500)
                      return res
                  booking["dates"].append(_date)
            res = make_response(jsonify({"message": "movie added"}), 200)
            write(bookings)
            return res

    bookings.append(req)
    write(bookings)
    res = make_response(jsonify({"message": "movie added"}), 200)
    return res


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
