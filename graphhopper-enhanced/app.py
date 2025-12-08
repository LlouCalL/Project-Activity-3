from flask import Flask, render_template, request, jsonify 
import requests
from collections import defaultdict

app = Flask(__name__)

# GraphHopper API Key
GRAPHOPPER_API_KEY = "7fc6933f-2209-4248-8ca4-d11d6eacfd68"

# --- ANALYTICS DATA STORAGE ---
route_stats = defaultdict(int)
vehicle_usage = defaultdict(int)

# --- Helper: Convert location name → coordinates ---
def geocode_location(location, api_key):
    geocode_url = "https://graphhopper.com/api/1/geocode"
    params = {"q": location, "limit": 1, "key": api_key, "country": "PH"}
    response = requests.get(geocode_url, params=params)
    response.raise_for_status()
    data = response.json()

    if not data["hits"]:
        raise ValueError(f"Could not find location: {location}")

    lat = data["hits"][0]["point"]["lat"]
    lng = data["hits"][0]["point"]["lng"]
    return lat, lng

# --- Helper: Format milliseconds → h, m, s ---
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

# --- Helper: Convert meters → km / miles ---
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

# --- ROUTE API ---
@app.route("/get_route", methods=["POST"])
def get_route():
    try:
        data = request.get_json()
        from_loc = data["from"]
        to_loc = data["to"]
        vehicle = data["vehicle"]
        unit = data.get("unit", "km")

        # Geocoding
        from_lat, from_lng = geocode_location(from_loc, GRAPHOPPER_API_KEY)
        to_lat, to_lng = geocode_location(to_loc, GRAPHOPPER_API_KEY)

        if abs(from_lat - to_lat) > 10 or abs(from_lng - to_lng) > 10:
            raise ValueError("Locations appear too far apart. Please specify more clearly.")

        # GraphHopper Routing API
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
        points = path["points"]["coordinates"]  # ✅ return GeoJSON coordinates
        distance_text = format_distance(path["distance"], unit)
        time_text = format_time(path["time"])

        instructions = [
            {
                "text": instr["text"],
                "distance": format_distance(instr["distance"], unit),
                "interval": instr["interval"]
            }
            for instr in path["instructions"]
        ]

        # --- ANALYTICS TRACKING ---
        route_key = f"{from_loc} → {to_loc}"
        route_stats[route_key] += 1
        vehicle_usage[vehicle] += 1

        return jsonify({
            "distance": distance_text,
            "time": time_text,
            "vehicle": vehicle.title(),
            "instructions": instructions,
            "points": points,
            "from": from_loc,
            "to": to_loc,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400

# --- ANALYTICS API ---
@app.route("/analytics", methods=["GET"])
def analytics():
    top_routes = sorted(route_stats.items(), key=lambda x: x[1], reverse=True)[:5]
    vehicle_data = dict(vehicle_usage)

    return jsonify({
        "top_routes": [{"route": r, "count": c} for r, c in top_routes],
        "vehicle_usage": vehicle_data
    })

if __name__ == "__main__":
    app.run(debug=True)
