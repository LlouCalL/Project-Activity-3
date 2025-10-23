import requests
import urllib.parse
from colorama import Fore, Style, init
from tabulate import tabulate

init(autoreset=True)  # Initialize colorama for colored text

ROUTE_URL = "https://graphhopper.com/api/1/route?"
KEY = "7fc6933f-2209-4248-8ca4-d11d6eacfd68"

def geocoding(location, key):
    """Convert a location name into coordinates using GraphHopper Geocoding API."""
    while location == "":
        location = input("Enter the location again: ")

    geocode_url = "https://graphhopper.com/api/1/geocode?"
    url = geocode_url + urllib.parse.urlencode({"q": location, "limit": "1", "key": key})
    response = requests.get(url)
    json_data = response.json()

    if response.status_code == 200 and len(json_data["hits"]) != 0:
        point = json_data["hits"][0]["point"]
        name = json_data["hits"][0]["name"]
        country = json_data["hits"][0].get("country", "")
        state = json_data["hits"][0].get("state", "")
        new_loc = f"{name}, {state}, {country}".strip(", ")
        print(f"{Fore.CYAN}Geocoding: {new_loc} ({json_data['hits'][0]['osm_value']})")
        return 200, point["lat"], point["lng"], new_loc
    else:
        print(f"{Fore.RED}Geocode Error: {json_data.get('message', 'Invalid location')}")
        return response.status_code, None, None, location

def route(orig, dest, vehicle, key):
    """Get route details using GraphHopper Routing API."""
    op = f"&point={orig[1]}%2C{orig[2]}"
    dp = f"&point={dest[1]}%2C{dest[2]}"
    url = ROUTE_URL + urllib.parse.urlencode({"key": key, "vehicle": vehicle}) + op + dp
    response = requests.get(url)
    data = response.json()
    return response.status_code, data, url

def display_route(data, vehicle, orig, dest, units="metric"):
    """Display route summary and directions."""
    path = data["paths"][0]
    dist_km = path["distance"] / 1000
    dist_mi = dist_km / 1.61
    hr, min, sec = int(path["time"]/1000/3600), int(path["time"]/1000/60 % 60), int(path["time"]/1000 % 60)

    print(f"\n{Fore.GREEN}{'='*60}")
    print(f"Directions from {orig[3]} to {dest[3]} by {vehicle}")
    print(f"{'='*60}")

    if units == "imperial":
        print(f"Distance Traveled: {dist_mi:.2f} miles")
    else:
        print(f"Distance Traveled: {dist_km:.2f} km")

    print(f"Trip Duration: {hr:02d}:{min:02d}:{sec:02d}")
    print(f"{'='*60}")

    table_data = []
    for step in path["instructions"]:
        step_text = step["text"]
        step_km = step["distance"] / 1000
        step_mi = step_km / 1.61
        if units == "imperial":
            table_data.append([step_text, f"{step_mi:.2f} miles"])
        else:
            table_data.append([step_text, f"{step_km:.2f} km"])

    print(tabulate(table_data, headers=["Instruction", f"Distance ({'mi' if units == 'imperial' else 'km'})"], tablefmt="grid"))

def main():
    print(f"{Fore.YELLOW}Welcome to the Enhanced GraphHopper Routing Application")
    print("Type 'quit' anytime to exit.\n")

    while True:
        print(f"{Fore.MAGENTA}Available Profiles: car, bike, foot")
        vehicle = input("Enter vehicle profile: ").lower()
        if vehicle in ["quit", "q"]:
            break
        elif vehicle not in ["car", "bike", "foot"]:
            vehicle = "car"
            print(f"{Fore.RED}Invalid profile! Using 'car'.")

        loc1 = input("Starting Location: ")
        if loc1.lower() in ["quit", "q"]:
            break
        orig = geocoding(loc1, KEY)

        loc2 = input("Destination: ")
        if loc2.lower() in ["quit", "q"]:
            break
        dest = geocoding(loc2, KEY)

        unit_choice = input("Use metric or imperial units? (m/i): ").lower()
        units = "imperial" if unit_choice == "i" else "metric"

        if orig[0] == 200 and dest[0] == 200:
            status, data, url = route(orig, dest, vehicle, KEY)
            if status == 200:
                display_route(data, vehicle, orig, dest, units)
            else:
                print(f"{Fore.RED}Error: {data.get('message', 'Unknown error')}")
        else:
            print(f"{Fore.RED}Could not fetch one or both locations.")

if __name__ == "__main__":
    main()

