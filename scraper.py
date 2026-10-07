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
    elif "snow" in text or "flurries" in text:
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
    url = "https://hs.newpaltz.k12.ny.us/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Get all text content from the homepage
        page_text = soup.get_text(separator=" ")
        
        # Search for patterns like "Today is a B Day", "Today is an A Day", or "Day B"
        match = re.search(r"Today\s+is\s+an?\s+([A-D])\s+Day", page_text, re.IGNORECASE)
        
        if not match:
            # Secondary check for short patterns like "Cycle Day: B" or "Day B"
            match = re.search(r"(?:Cycle\s+)?Day\s+([A-D])\b", page_text, re.IGNORECASE)
            
        if match:
            cycle_letter = match.group(1).upper()
            cycle_day_text = f"Today is a {cycle_letter} Day"
        else:
            cycle_letter = "--"
            cycle_day_text = "No School! 😁"
            
        return {
            "cycle_letter": cycle_letter,
            "cycle_day_text": cycle_day_text
        }
        
    except Exception as e:
        print(f"School scraping error: {e}")
        return {
            "cycle_letter": "--",
            "cycle_day_text": "Schedule Unavailable"
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
        "today_temp": weather_data["today_temp"],
        "today_icon": weather_data["today_icon"],
        "today_cond": weather_data["today_cond"],
        "tomorrow_temp": weather_data["tomorrow_temp"],
        "tomorrow_icon": weather_data["tomorrow_icon"],
        "tomorrow_cond": weather_data["tomorrow_cond"],
        "cycle_letter": school_data["cycle_letter"],
        "cycle_day_text": school_data["cycle_day_text"]
    }

    send_to_trmnl(combined_payload)
