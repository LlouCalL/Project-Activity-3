from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# GraphHopper API key
GRAPHOPPER_API_KEY = "7fc6933f-2209-4248-8ca4-d11d6eacfd68"


# --- Helper: Convert location name → coordinates
def geocode_location(location, api_key):
    geocode_url = "https://graphhopper.com/api/1/geocode"
    params = {"q": location, "limit": 1, "key": api_key, "country": "PH"}  # Restrict to PH
    response = requests.get(geocode_url, params=params)
    response.raise_for_status()
    data = response.json()

    if not data["hits"]:
        raise ValueError(f"Could not find location: {location}")

    lat = data["hits"][0]["point"]["lat"]
    lng = data["hits"][0]["point"]["lng"]
    return lat, lng


# --- Helper: Format milliseconds → h, m, s
def format_time(milliseconds):
    total_seconds = int(milliseconds / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


# --- Helper: Convert meters → km or miles
def format_distance(meters, unit):
    if unit.lower().startswith("mile"):
        miles = meters / 1609.34
        return f"{miles:.2f} mi"
    else:
        kilometers = meters / 1000
        return f"{kilometers:.2f} km"


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_route", methods=["POST"])
def get_route():
    try:
        data = request.get_json()
        from_loc = data["from"]
        to_loc = data["to"]
        vehicle = data["vehicle"]
        unit = data.get("unit", "km")

        # Geocode both addresses
        from_lat, from_lng = geocode_location(from_loc, GRAPHOPPER_API_KEY)
        to_lat, to_lng = geocode_location(to_loc, GRAPHOPPER_API_KEY)

        # Sanity check: prevent far-off mismatches
        if abs(from_lat - to_lat) > 10 or abs(from_lng - to_lng) > 10:
            raise ValueError("Detected locations too far apart. Please specify more clearly.")

        # GraphHopper routing request
        route_url = "https://graphhopper.com/api/1/route"
        params = {
            "point": [f"{from_lat},{from_lng}", f"{to_lat},{to_lng}"],
            "vehicle": vehicle,
            "locale": "en",
            "points_encoded": "false",
            "key": GRAPHOPPER_API_KEY,
        }

        response = requests.get(route_url, params=params)
        response.raise_for_status()
        route_data = response.json()

        if not route_data.get("paths"):
            raise ValueError("No route found between these points.")

        path = route_data["paths"][0]
        points = path["points"]
        distance_text = format_distance(path["distance"], unit)
        time_text = format_time(path["time"])

        instructions = [
            {"text": instr["text"], "distance": format_distance(instr["distance"], unit)}
            for instr in path["instructions"]
        ]

        return jsonify({
            "distance": distance_text,
            "time": time_text,
            "vehicle": vehicle.title(),
            "instructions": instructions,
            "points": points,
        })

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)
