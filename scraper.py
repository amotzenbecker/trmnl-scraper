import os
import sys
import requests
from bs4 import BeautifulSoup

TRMNL_WEBHOOK_URL = os.environ.get("TRMNL_WEBHOOK_URL")
SCHOOL_URL = "https://hs.newpaltz.k12.ny.us/"
FORECAST_URL = "https://api.weather.gov/gridpoints/ALY/67,20/forecast"

HEADERS = {
    # NOAA requires a unique User-Agent header (include an email or app name)
    "User-Agent": "NewPaltzTrmnlDisplay/1.0 (amotz-trmnl-display)"
}


def get_noaa_weather():
    """Fetches forecast directly using the hard-coded gridpoint URL."""
    try:
        response = requests.get(FORECAST_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        periods = response.json()["properties"]["periods"]
        current = periods[0]  # Today/Tonight's forecast

        return {
            "temp": f"{current['temperature']}°{current['temperatureUnit']}",
            "condition": current["shortForecast"],
            "wind": f"{current['windSpeed']} {current['windDirection']}"
        }
    except Exception as e:
        print(f"Weather fetch failed: {e}")
        return {
            "temp": "--°F",
            "condition": "Weather Unavailable",
            "wind": "--"
        }

def scrape_high_school_site():
    """Scrapes the New Paltz High School homepage for announcements."""
    response = requests.get(SCHOOL_URL, headers=HEADERS, timeout=15)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch site. HTTP Status: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    
    headlines = []
    for heading in soup.find_all(['h2', 'h3', 'a'], limit=10):
        text = heading.get_text(strip=True)
        if text and len(text) > 15 and text not in headlines:
            headlines.append(text)

    return {
        "announcement_1": headlines[0] if len(headlines) > 0 else "No recent announcements.",
        "announcement_2": headlines[1] if len(headlines) > 1 else ""
    }


def send_to_trmnl(data):
    """Posts combined payload to the TRMNL webhook."""
    if not TRMNL_WEBHOOK_URL:
        print("ERROR: TRMNL_WEBHOOK_URL environment variable is missing.")
        sys.exit(1)

    payload = {"merge_variables": data}
    print("Sending payload to TRMNL:", payload)

    res = requests.post(TRMNL_WEBHOOK_URL, json=payload, timeout=10)
    if res.status_code == 200:
        print("Successfully updated TRMNL display!")
    else:
        print(f"Failed to update TRMNL. Status Code: {res.status_code}, Response: {res.text}")
        sys.exit(1)


if __name__ == "__main__":
    # Fetch data from both sources
    weather_data = get_noaa_weather()
    school_data = scrape_high_school_site()

    # Combine into a single dictionary
    combined_payload = {
        "school_title": "New Paltz High School",
        "weather_temp": weather_data["temp"],
        "weather_condition": weather_data["condition"],
        "weather_wind": weather_data["wind"],
        "announcement_1": school_data["announcement_1"],
        "announcement_2": school_data["announcement_2"]
    }

    send_to_trmnl(combined_payload)
