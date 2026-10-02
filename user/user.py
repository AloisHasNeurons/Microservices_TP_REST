from flask import Flask, render_template, request, jsonify, make_response
import requests
import json
from werkzeug.exceptions import NotFound

app = Flask(__name__)

PORT = 3203
HOST = '0.0.0.0'

current_user = {
      "id": "chris_rivers",
      "name": "Chris Rivers",
      "last_active":1360031010,
      "admin": True
}

with open('{}/databases/users.json'.format("."), "r") as jsf:
   users = json.load(jsf)["users"]

def write(users):
    with open("{}/databases/users.json".format("."), "w") as f:
        full = {}
        full["users"] = users
        json.dump(full, f)

@app.route("/", methods=['GET'])
def home():
   return "<h1 style='color:blue'>Welcome to the User service!</h1>"

@app.route("/json", methods=["GET"])
def get_json():
    if not current_user["admin"]:
       make_response(jsonify({"error" : "forbidden"}), 403)
    res = make_response(jsonify(users), 200)
    return res

@app.route("/user/<user_id>", methods=["GET"])
def get_user_id(user_id):
    if not (current_user["admin"] or user_id==str(current_user["id"])):
       return(make_response(jsonify({"error" : "forbidden"}), 403))
    for user in users :
       if user_id==str(user["id"]):
          return (make_response(jsonify(user), 200))
    return (make_response(jsonify({"error" : "Not found"}), 404))

@app.route("/user/admin", methods=["GET"])
def get_admin():
    if not current_user["admin"]:
       return(make_response(jsonify({"error" : "forbidden"}), 403))
    for user in users :
       rep = [user for user in users if user["admin"]]
       return (make_response(jsonify(rep), 200))
    return (make_response(jsonify({"error" : "Not found"}), 404))

@app.route("/user/<user_id>", methods=["POST"])
def create_user(user_id):
    for user in users :
       if user_id==str(user["id"]):
          return (make_response(jsonify({"error": "user ID already exists"}), 500))
    req = request.get_json()
    if req["admin"] and not current_user["admin"]:
       return (make_response(jsonify({"error" : "forbidden"}), 403))
    users.append(req)
    write(users)
    return (make_response(jsonify(req), 200))

@app.route("/user/<user_id>", methods=["PUT"])
def modify_user(user_id):
    user_exist=False
    req = request.get_json()
    if req["admin"] and not current_user["admin"]:
      return (make_response(jsonify({"error" : "forbidden"}), 403))
    for i in range (len(users)) :
       if user_id==str(users[i]["id"]):
          users[i] = req
          users[i]["id"]=user_id
          user_exist=True
    if not user_exist : 
       return (make_response(jsonify({"error" : "user not found"}), 404))
    write(users)
    return (make_response(jsonify(req), 200))

@app.route("/user/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    if not (current_user["admin"] or user_id==str(current_user["id"])):
       return(make_response(jsonify({"error" : "forbidden"}), 403))
    for user in users :
       if user_id==str(user["id"]):
          users.remove(user)
          write(users)
          return (make_response("succesfully deleted"),204)
    return (make_response(jsonify({"error" : "user not found"}), 404))

if __name__ == "__main__":
   print("Server running in port %s"%(PORT))
   app.run(host=HOST, port=PORT)
