from pathlib import Path
from datetime import datetime
import sqlite3

from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# =========================================================
#  GraphHopper API key
#  TIP: put your real key here or load from env.
# =========================================================
GRAPHOPPER_API_KEY = "YOUR_GRAPHHOPPER_API_KEY_HERE"

# =========================================================
#  SQLite setup for "Favorite Routes"
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "favorites.db"


def get_db_connection():
    """Open a connection to the favorites SQLite DB."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the favorites table if it does not exist."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
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
        """
    )
    conn.commit()
    conn.close()


@app.before_first_request
def startup():
    """Initialize DB on first request."""
    init_db()


# =========================================================
#  Helper: Convert location name → coordinates
# =========================================================
def geocode_location(location: str, api_key: str):
    geocode_url = "https://graphhopper.com/api/1/geocode"
    params = {
        "q": location,
        "limit": 1,
        "key": api_key,
        "country": "PH",  # Restrict to PH
    }

    response = requests.get(geocode_url, params=params)
    response.raise_for_status()
    data = response.json()

    if not data["hits"]:
        raise ValueError(f"Could not find location: {location}")

    lat = data["hits"][0]["point"]["lat"]
    lng = data["hits"][0]["point"]["lng"]
    return lat, lng


# =========================================================
#  Helper: Format time & distance
# =========================================================
def format_time(milliseconds: int) -> str:
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


def format_distance(meters: float, unit: str) -> str:
    if unit.lower().startswith("mile"):
        miles = meters / 1609.34
        return f"{miles:.2f} mi"
    else:
        kilometers = meters / 1000
        return f"{kilometers:.2f} km"


# =========================================================
#  Routes
# =========================================================
@app.route("/")
def index():
    """Render main page."""
    return render_template("index.html")


@app.route("/get_route", methods=["POST"])
def get_route():
    """
    Main routing endpoint.
    Returns data that frontend can also use to save as favorite.
    """
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
            raise ValueError(
                "Detected locations too far apart. Please specify more clearly."
            )

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
            {
                "text": instr["text"],
                "distance": format_distance(instr["distance"], unit),
            }
            for instr in path["instructions"]
        ]

        # from/to included so frontend can save as favorite easily
        return jsonify(
            {
                "distance": distance_text,
                "time": time_text,
                "vehicle": vehicle.title(),
                "unit": unit,
                "instructions": instructions,
                "points": points,
                "from": from_loc,
                "to": to_loc,
            }
        )

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 400


# ---------- Autocomplete endpoint ----------
@app.route("/autocomplete", methods=["GET"])
def autocomplete():
    try:
        query = request.args.get("q", "")
        if not query:
            return jsonify([])

        geocode_url = "https://graphhopper.com/api/1/geocode"
        params = {
            "q": query,
            "limit": 5,  # Fetch up to 5 results
            "key": GRAPHOPPER_API_KEY,
            "country": "PH",
            "autocomplete": "true",  # Important for autocomplete
        }

        response = requests.get(geocode_url, params=params)
        response.raise_for_status()
        data = response.json()

        # Extract only the name/location text for the autocomplete list
        suggestions = [hit["name"] for hit in data.get("hits", [])]
        return jsonify(suggestions)

    except Exception as e:
        print("Autocomplete Error:", e)
        # Return an empty list on error to prevent breaking the frontend
        return jsonify([])


# =========================================================
#  Favorite Routes API (SQLite-backed)
# =========================================================
@app.route("/favorites", methods=["GET"])
def list_favorites():
    """
    Return all saved favorite routes.
    """
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT
            id,
            name,
            origin,
            destination,
            vehicle,
            unit,
            distance_text,
            time_text,
            created_at
        FROM favorites
        ORDER BY datetime(created_at) DESC
        """
    ).fetchall()
    conn.close()

    favorites = [
        {
            "id": row["id"],
            "name": row["name"],
            "origin": row["origin"],
            "destination": row["destination"],
            "vehicle": row["vehicle"],
            "unit": row["unit"],
            "distance": row["distance_text"],
            "time": row["time_text"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return jsonify(favorites)


@app.route("/favorites", methods=["POST"])
def add_favorite():
    """
    Save a favorite route.

    Expected JSON body:
    {
      "name": "Weekend trip",
      "from": "Manila",
      "to": "Tagaytay",
      "vehicle": "car",
      "unit": "km",
      "distance": "65.20 km",
      "time": "1h 30m 0s"
    }
    """
    try:
        data = request.get_json() or {}

        name = (data.get("name") or "").strip()
        origin = (data.get("from") or "").strip()
        destination = (data.get("to") or "").strip()
        vehicle = (data.get("vehicle") or "car").strip()
        unit = (data.get("unit") or "km").strip()
        distance_text = (data.get("distance") or "").strip()
        time_text = (data.get("time") or "").strip()

        if not (name and origin and destination and distance_text and time_text):
            return jsonify(
                {"error": "Missing required fields to save favorite route."}
            ), 400

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO favorites
            (name, origin, destination, vehicle, unit, distance_text, time_text, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                origin,
                destination,
                vehicle,
                unit,
                distance_text,
                time_text,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        fav_id = cur.lastrowid
        conn.close()

        return jsonify(
            {"id": fav_id, "message": "Favorite route saved successfully."}
        ), 201

    except Exception as e:
        print("Add favorite error:", e)
        return jsonify({"error": str(e)}), 400


@app.route("/favorites/<int:fav_id>", methods=["DELETE"])
def delete_favorite(fav_id: int):
    """
    Delete a favorite route by ID.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM favorites WHERE id = ?", (fav_id,))
    conn.commit()
    deleted = cur.rowcount
    conn.close()

    if deleted == 0:
        return jsonify({"error": "Favorite not found."}), 404

    return jsonify({"message": "Favorite route deleted."})


if __name__ == "__main__":
    app.run(debug=True)
