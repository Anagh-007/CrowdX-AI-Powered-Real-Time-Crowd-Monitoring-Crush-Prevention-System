import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")

def get_location():

    # 🔥 TRY GOOGLE API FIRST
    try:
        url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={API_KEY}"
        response = requests.post(url, json={})
        data = response.json()

        lat = data.get("location", {}).get("lat")
        lon = data.get("location", {}).get("lng")

        if lat and lon:
            maps_link = f"https://www.google.com/maps?q={lat},{lon}"
            return lat, lon, maps_link

    except:
        pass

    # 🔥 FALLBACK (HARDCODE — ACCURATE DEMO)
    print("⚠️ Using fallback location")

    lat = 12.9716   # CHANGE TO YOUR REAL PLACE
    lon = 77.5946

    maps_link = f"https://www.google.com/maps?q={lat},{lon}"

    return lat, lon, maps_link