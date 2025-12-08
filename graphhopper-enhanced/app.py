from pathlib import Path
from datetime import datetime
import sqlite3

from flask import Flask, render_template, request, jsonify
import requests
from requests.exceptions import Timeout, RequestException

app = Flask(__name__)

# =========================================================
#  GraphHopper API key
# =========================================================
GRAPHOPPER_API_KEY = "7fc6933f-2209-4248-8ca4-d11d6eacfd68"

# =========================================================
#  SQLite setup
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "favorites.db"

def get_db_connection():
    """Open a connection to the favorites SQLite DB."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Favorites Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            unit TEXT NOT NULL,
            distance_text TEXT NOT NULL,
            time_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # 2. History Table for Analytics
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Run DB init ONCE at startup
with app.app_context():
    init_db()


# =========================================================
#  Helpers
# =========================================================
LOCATION_FALLBACKS = {
    "batangas city": (13.7565, 121.0583),
    "luisiana, laguna": (14.1726, 121.5048),
    "manila": (14.5995, 120.9842),
}

def geocode_location(location: str, api_key: str):
    geocode_url = "https://graphhopper.com/api/1/geocode"
    params = {"q": location, "limit": 1, "key": api_key, "country": "PH"}

    try:
        response = requests.get(geocode_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("hits"):
            return data["hits"][0]["point"]["lat"], data["hits"][0]["point"]["lng"]
    except (Timeout, RequestException) as e:
        print(f"Geocoding failed ({e}), trying fallback.")

    key = location.strip().lower()
    if key in LOCATION_FALLBACKS:
        return LOCATION_FALLBACKS[key]
    raise ValueError(f"Could not find location: {location}")


def format_time(milliseconds: int) -> str:
    total_seconds = int(milliseconds / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0: return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0: return f"{minutes}m {seconds}s"
    else: return f"{seconds}s"


def format_distance(meters: float, unit: str) -> str:
    if unit.lower().startswith("mile"):
        return f"{meters / 1609.34:.2f} mi"
    return f"{meters / 1000:.2f} km"


def log_analytics(origin, destination, vehicle):
    """Log a route request to the history table."""
    try:
        conn = get_db_connection()
        conn.execute(
            "INSERT INTO history (origin, destination, vehicle, timestamp) VALUES (?, ?, ?, ?)",
            (origin, destination, vehicle, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log history: {e}")


# =========================================================
#  Routes
# =========================================================
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

        # 1. Geocode
        from_lat, from_lng = geocode_location(from_loc, GRAPHOPPER_API_KEY)
        to_lat, to_lng = geocode_location(to_loc, GRAPHOPPER_API_KEY)

        if abs(from_lat - to_lat) > 10 or abs(from_lng - to_lng) > 10:
            raise ValueError("Locations too far apart.")

        # 2. Route Request
        route_url = "https://graphhopper.com/api/1/route"
        params = {
            "point": [f"{from_lat},{from_lng}", f"{to_lat},{to_lng}"],
            "vehicle": vehicle,
            "locale": "en",
            "points_encoded": "false",
            "key": GRAPHOPPER_API_KEY,
        }

        try:
            response = requests.get(route_url, params=params, timeout=40)
            response.raise_for_status()
        except Exception as e:
            return jsonify({"error": f"Routing service error: {e}"}), 502

        route_data = response.json()
        if not route_data.get("paths"):
            raise ValueError("No route found.")

        path = route_data["paths"][0]
        points = path["points"]
        distance_text = format_distance(path["distance"], unit)
        time_text = format_time(path["time"])

        instructions = [
            {
                "text": instr["text"],
                "distance": format_distance(instr["distance"], unit),
            }
            for instr in path["instructions"]
        ]

        # 3. Log to Analytics (This was the missing piece)
        log_analytics(from_loc, to_loc, vehicle)

        return jsonify({
            "distance": distance_text,
            "time": time_text,
            "vehicle": vehicle.title(),
            "unit": unit,
            "instructions": instructions,
            "points": points,
            "from": from_loc,
            "to": to_loc,
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Unexpected server error."}), 500


@app.route("/favorites", methods=["GET"])
def list_favorites():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM favorites ORDER BY created_at DESC").fetchall()
    conn.close()
    
    # Convert Row objects to dicts
    favorites = [dict(row) for row in rows]
    # Map distance_text -> distance for frontend compatibility if needed
    for f in favorites:
        f['distance'] = f['distance_text']
        f['time'] = f['time_text']
        
    return jsonify(favorites)


@app.route("/favorites", methods=["POST"])
def add_favorite():
    try:
        data = request.get_json() or {}
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO favorites
            (name, origin, destination, vehicle, unit, distance_text, time_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data.get("name"),
                data.get("from"),
                data.get("to"),
                data.get("vehicle"),
                data.get("unit"),
                data.get("distance"),
                data.get("time"),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        fav_id = cur.lastrowid
        conn.close()
        return jsonify({"id": fav_id, "message": "Saved."}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/favorites/<int:fav_id>", methods=["DELETE"])
def delete_favorite(fav_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM favorites WHERE id = ?", (fav_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Deleted."})


@app.route("/analytics_data")
def analytics_data():
    conn = get_db_connection()
    
    # Top 5 Routes
    top_routes = conn.execute("""
        SELECT origin || ' → ' || destination as route, COUNT(*) as count 
        FROM history 
        GROUP BY origin, destination 
        ORDER BY count DESC 
        LIMIT 5
    """).fetchall()

    # Vehicle Usage
    vehicle_stats = conn.execute("""
        SELECT vehicle, COUNT(*) as count 
        FROM history 
        GROUP BY vehicle
    """).fetchall()
    
    conn.close()

    return jsonify({
        "top_routes": [{"label": r["route"], "count": r["count"]} for r in top_routes],
        "vehicles": [{"label": r["vehicle"], "count": r["count"]} for r in vehicle_stats]
    })


if __name__ == "__main__":
    app.run(debug=True)