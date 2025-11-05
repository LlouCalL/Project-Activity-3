from flask import Flask, render_template, request, jsonify
import requests
import os

app = Flask(__name__)

GRAPHOPPER_KEY = os.getenv("GRAPHOPPER_KEY", "7fc6933f-2209-4248-8ca4-d11d6eacfd68")

# Helper function to call GraphHopper API
def call_graphhopper(endpoint, params):
    try:
        params["key"] = GRAPHOPPER_KEY
        resp = requests.get(f"https://graphhopper.com/api/1/{endpoint}", params=params)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/geocode")
def geocode():
    query = request.args.get("q", "")
    if not query:
        return jsonify({"error": "Missing location query."}), 400

    data = call_graphhopper("geocode", {"q": query, "limit": 1})
    return jsonify(data)


@app.route("/api/route")
def route():
    try:
        orig = request.args.get("orig")
        dest = request.args.get("dest")
        vehicle = request.args.get("vehicle", "car")

        if not orig or not dest:
            return jsonify({"error": "Origin and destination required."}), 400

        o_lat, o_lng = map(float, orig.split(","))
        d_lat, d_lng = map(float, dest.split(","))

        params = {
            "point": [f"{o_lat},{o_lng}", f"{d_lat},{d_lng}"],
            "vehicle": vehicle,
        }
        data = call_graphhopper("route", params)
        return jsonify(data)
    except ValueError:
        return jsonify({"error": "Invalid coordinates."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
