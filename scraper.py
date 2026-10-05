import os
import re
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

def get_weather_icon(condition_text):
    """Maps NOAA forecast condition text to TRMNL hosted SVG icons."""
    text = condition_text.lower()
    if "sun" in text or "clear" in text:
        icon = "wi-day-sunny"
    elif "rain" in text or "shower" in text:
        icon = "wi-day-rain"
    elif "snow" in text or "flurr" in text:
        icon = "wi-day-snow"
    elif "thunder" in text or "storm" in text:
        icon = "wi-day-thunderstorm"
    elif "cloud" in text or "overcast" in text:
        icon = "wi-day-cloudy"
    elif "fog" in text or "haze" in text:
        icon = "wi-day-fog"
    else:
        icon = "wi-day-sunny"
    return f"https://trmnl.com/images/plugins/weather/{icon}.svg"

def get_noaa_weather():
    url = "https://api.weather.gov/gridpoints/ALY/67,20/forecast"
    headers = {"User-Agent": "NewPaltzTrmnlDisplay/1.0 (contact@example.com)"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        periods = response.json()["properties"]["periods"]
        
        # Helper to extract numeric temperature integer
        def get_temp(p):
            return p["temperature"]

        # Today vs Tomorrow grouping
        # If running early in the day: period[0] is Today (Hi), period[1] is Tonight (Lo)
        # If running late at night: period[0] is Tonight (Lo)
        if periods[0]["isDaytime"]:
            today_hi = f"{get_temp(periods[0])}°"
            today_lo = f"{get_temp(periods[1])}°"
            today_cond = periods[0]["shortForecast"]
            today_icon = get_weather_icon(today_cond)
            
            tomorrow_hi = f"{get_temp(periods[2])}°"
            tomorrow_lo = f"{get_temp(periods[3])}°"
            tomorrow_cond = periods[2]["shortForecast"]
            tomorrow_icon = get_weather_icon(tomorrow_cond)
        else:
            today_hi = "--°"
            today_lo = f"{get_temp(periods[0])}°"
            today_cond = periods[0]["shortForecast"]
            today_icon = get_weather_icon(today_cond)
            
            tomorrow_hi = f"{get_temp(periods[1])}°"
            tomorrow_lo = f"{get_temp(periods[2])}°"
            tomorrow_cond = periods[1]["shortForecast"]
            tomorrow_icon = get_weather_icon(tomorrow_cond)

        return {
            "today_temp": f"{today_hi} / {today_lo}",
            "today_icon": today_icon,
            "today_cond": today_cond,
            "tomorrow_temp": f"{tomorrow_hi} / {tomorrow_lo}",
            "tomorrow_icon": tomorrow_icon,
            "tomorrow_cond": tomorrow_cond
        }
    except Exception as e:
        print(f"Weather error: {e}")
        return {
            "today_temp": "--° / --°", "today_icon": "", "today_cond": "N/A",
            "tomorrow_temp": "--° / --°", "tomorrow_icon": "", "tomorrow_cond": "N/A"
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
