import pytest
import requests_mock
import json
import sqlite3
import os

# Import the Flask application and helper functions from app.py
# The core logic relies on these imported functions.
from app import app, get_db_connection, format_distance, format_time, init_db

# --- MOCK DATA ---
# This data simulates the response from the external GraphHopper APIs.
MOCK_ROUTE_SUCCESS = {
    "paths": [
        {
            "distance": 50000.0,  # 50 km
            "time": 3600000,      # 1 hour
            "points": "polyline_string_data",
            "instructions": [
                {"distance": 1000.0, "text": "Start"},
                {"distance": 49000.0, "text": "Arrive"},
            ]
        }
    ]
}

MOCK_GEOCODE_SUCCESS = {
    "hits": [
        {"point": {"lat": 14.5995, "lng": 120.9842}} # Mocked coordinates
    ]
}

MOCK_ROUTE_FAILURE = {"paths": []}


@pytest.fixture
def client():
    """
    Configures the Flask application for testing using a clean, in-memory
    SQLite database for each test. This ensures test isolation.
    """
    app.config['TESTING'] = True
    
    # 1. Temporarily override get_db_connection to use an in-memory DB
    original_get_db = get_db_connection
    def get_test_db_connection():
        # Connect to an in-memory DB (deleted when connection closed)
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        return conn

    # 2. Patch the application context to use the in-memory connection
    with app.app_context():
        # Replace the function temporarily
        app.get_db_connection = get_test_db_connection
        # Initialize the tables in the new in-memory connection
        init_db()

    # 3. Use the Flask test client
    with app.test_client() as client:
        yield client
    
    # 4. Clean up: Restore the original function reference after testing
    with app.app_context():
        app.get_db_connection = original_get_db

# --- Helper Function Unit Tests ---

def test_format_time():
    """Verify time conversion from milliseconds to human-readable format."""
    # 1 hour, 30 minutes, 15 seconds
    assert format_time(5415000) == "1h 30m 15s"
    # 45 seconds
    assert format_time(45000) == "45s"

def test_format_distance():
    """Verify distance conversion based on unit (km or miles)."""
    # 10,000 meters to km
    assert format_distance(10000, "km") == "10.00 km"
    # ~16093.4 meters to miles
    assert format_distance(16093.4, "mi") == "10.00 mi"


# --- Backend API & Integration Tests ---

# P-101: Index Page Load (Health Check)
def test_index_page(client):
    """Test the root URL loads successfully."""
    response = client.get("/")
    assert response.status_code == 200

# P-102: Successful Route Calculation (Mocked External API)
@requests_mock.Mocker(kw="mock")
def test_successful_route_calculation(client, mock):
    """Test /get_route returns a valid route by mocking the external GraphHopper API."""
    # Mock Geocoding
    mock.get("https://graphhopper.com/api/1/geocode", json=MOCK_GEOCODE_SUCCESS)
    # Mock Routing service
    mock.get("https://graphhopper.com/api/1/route", json=MOCK_ROUTE_SUCCESS)

    data = {
        "from": "Manila",
        "to": "Batangas City",
        "vehicle": "car",
        "unit": "km"
    }
    response = client.post("/get_route", json=data)
    
    assert response.status_code == 200
    route = response.get_json()
    
    # Assert expected data from MOCK_ROUTE_SUCCESS
    assert route["distance"] == "50.00 km"
    assert route["time"] == "1h 0m 0s"
    assert route["vehicle"] == "Car"

# P-103: Route Not Found (Mocked External API)
@requests_mock.Mocker(kw="mock")
def test_route_not_found(client, mock):
    """Test /get_route handles the case where the routing service finds no path."""
    # Mock Geocoding
    mock.get("https://graphhopper.com/api/1/geocode", json=MOCK_GEOCODE_SUCCESS)
    # Mock Routing service to return a failure response
    mock.get("https://graphhopper.com/api/1/route", json=MOCK_ROUTE_FAILURE)

    data = {
        "from": "Moon",
        "to": "Mars",
        "vehicle": "car",
        "unit": "km"
    }
    response = client.post("/get_route", json=data)
    
    assert response.status_code == 400
    assert "No route found." in response.get_json()["error"]

# P-104: Invalid API Request (Missing Parameters)
def test_missing_parameters(client):
    """Test /get_route gracefully handles missing required JSON fields."""
    # Missing 'from' field
    data = {
        "to": "Batangas City",
        "vehicle": "car",
        "unit": "km"
    }
    response = client.post("/get_route", json=data)
    
    # This should be caught by Flask's JSON parsing or the try/except block.
    assert response.status_code == 400
    assert "error" in response.get_json()

# P-105, P-106, P-107: Favorites CRUD Workflow (Integration with Data Layer)
def test_favorites_workflow(client):
    """Tests the sequence of adding, listing, and deleting a favorite."""
    
    # --- P-105: Save Favorite Route ---
    fav_data = {
        "name": "Test Route",
        "from": "A",
        "to": "B",
        "vehicle": "car",
        "unit": "km",
        "distance": "10 km",
        "time": "15 min",
    }
    response = client.post("/favorites", json=fav_data)
    assert response.status_code == 201
    favorite_id = response.get_json()["id"]
    
    # --- P-106: Retrieve Favorites ---
    response = client.get("/favorites")
    assert response.status_code == 200
    favorites_list = response.get_json()
    assert len(favorites_list) == 1
    assert favorites_list[0]["name"] == "Test Route"
    assert favorites_list[0]["origin"] == "A"
    
    # --- P-107: Delete Favorite Route ---
    response = client.delete(f"/favorites/{favorite_id}")
    assert response.status_code == 200
    
    # Verify deletion by listing again
    response = client.get("/favorites")
    assert len(response.get_json()) == 0

# P-108: Analytics Data Retrieval (Integration with Data Layer)
def test_analytics_data(client):
    """Test the retrieval and aggregation logic for top routes and vehicle usage."""
    
    # Manually log some sample data to the in-memory history table
    with app.app_context():
        conn = get_db_connection()
        # Log: Manila -> QC (Twice)
        conn.execute(
            "INSERT INTO history (origin, destination, vehicle, timestamp) VALUES (?, ?, ?, ?)",
            ("Manila", "QC", "car", "2023-01-01T00:00:00")
        )
        conn.execute(
            "INSERT INTO history (origin, destination, vehicle, timestamp) VALUES (?, ?, ?, ?)",
            ("Manila", "QC", "car", "2023-01-01T00:00:01")
        )
        # Log: Cebu -> Davao (Once, different vehicle)
        conn.execute(
            "INSERT INTO history (origin, destination, vehicle, timestamp) VALUES (?, ?, ?, ?)",
            ("Cebu", "Davao", "truck", "2023-01-01T00:00:02")
        )
        conn.commit()
        conn.close()

    response = client.get("/analytics_data")
    assert response.status_code == 200
    data = response.get_json()

    # Check Top Routes
    top_routes = data["top_routes"]
    assert len(top_routes) == 2
    assert top_routes[0]["label"] == "Manila → QC"
    assert top_routes[0]["count"] == 2
    
    # Check Vehicle Usage
    vehicles = data["vehicles"]
    assert len(vehicles) == 2
    vehicle_dict = {v["label"]: v["count"] for v in vehicles}
    assert vehicle_dict["car"] == 2
    assert vehicle_dict["truck"] == 1
