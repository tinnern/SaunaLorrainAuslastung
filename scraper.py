#!/usr/bin/env python3
"""
Sauna Lorraine Occupancy Tracker
Fetches and logs sauna occupancy data from the Lorrainebad API.
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API_URL = "https://lorauna.app/api"
GRAPHQL_QUERY = "{ allSaunas { name, current_seats, max_seats, capacity_message } }"
DATA_DIR = Path(__file__).parent / "data"
CSV_FILE = DATA_DIR / "occupancy_log.csv"
JSON_FILE = DATA_DIR / "occupancy_log.json"
CURRENT_FILE = DATA_DIR / "current.json"
WEATHER_STATS_FILE = DATA_DIR / "weather_stats.json"

# Open-Meteo API for Bern, Switzerland (46.948°N, 7.447°E)
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
BERN_LAT = 46.948
BERN_LON = 7.447

# Weather code descriptions (WMO codes)
WEATHER_CODES = {
    0: "Klar | Clear",
    1: "Überwiegend klar | Mainly clear",
    2: "Teilweise bewölkt | Partly cloudy",
    3: "Bewölkt | Overcast",
    45: "Nebel | Fog",
    48: "Nebel mit Reif | Depositing rime fog",
    51: "Leichter Nieselregen | Light drizzle",
    53: "Mässiger Nieselregen | Moderate drizzle",
    55: "Dichter Nieselregen | Dense drizzle",
    61: "Leichter Regen | Slight rain",
    63: "Mässiger Regen | Moderate rain",
    65: "Starker Regen | Heavy rain",
    66: "Leichter Gefrierregen | Light freezing rain",
    67: "Starker Gefrierregen | Heavy freezing rain",
    71: "Leichter Schneefall | Slight snow",
    73: "Mässiger Schneefall | Moderate snow",
    75: "Starker Schneefall | Heavy snow",
    77: "Schneekörner | Snow grains",
    80: "Leichte Regenschauer | Slight rain showers",
    81: "Mässige Regenschauer | Moderate rain showers",
    82: "Heftige Regenschauer | Violent rain showers",
    85: "Leichte Schneeschauer | Slight snow showers",
    86: "Starke Schneeschauer | Heavy snow showers",
    95: "Gewitter | Thunderstorm",
    96: "Gewitter mit leichtem Hagel | Thunderstorm with slight hail",
    99: "Gewitter mit starkem Hagel | Thunderstorm with heavy hail"
}


def fetch_occupancy():
    """Fetch current occupancy data from the API."""
    try:
        response = requests.post(
            API_URL,
            json={"query": GRAPHQL_QUERY},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("allSaunas", [])
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None


def fetch_weather():
    """Fetch current weather data from Open-Meteo API for Bern."""
    try:
        params = {
            "latitude": BERN_LAT,
            "longitude": BERN_LON,
            "current": "temperature_2m,relative_humidity_2m,precipitation,weather_code,cloud_cover,apparent_temperature",
            "timezone": "Europe/Zurich"
        }
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data.get("current", {})

        weather_code = current.get("weather_code", 0)
        return {
            "temperature": current.get("temperature_2m"),
            "apparent_temperature": current.get("apparent_temperature"),
            "humidity": current.get("relative_humidity_2m"),
            "precipitation": current.get("precipitation", 0),
            "weather_code": weather_code,
            "weather_description": WEATHER_CODES.get(weather_code, "Unbekannt | Unknown"),
            "cloud_cover": current.get("cloud_cover"),
            "is_rainy": current.get("precipitation", 0) > 0 or weather_code in [51, 53, 55, 61, 63, 65, 66, 67, 80, 81, 82],
            "is_sunny": weather_code in [0, 1] and current.get("cloud_cover", 100) < 30
        }
    except requests.RequestException as e:
        print(f"Error fetching weather: {e}")
        return None


def load_existing_data():
    """Load existing JSON data."""
    if JSON_FILE.exists():
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_json_data(records):
    """Save data to JSON file."""
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def save_current(saunas, timestamp, weather=None):
    """Save current state for quick access."""
    current = {
        "timestamp": timestamp,
        "saunas": []
    }
    for sauna in saunas:
        current_seats = sauna.get("current_seats", 0)
        max_seats = sauna.get("max_seats", 1)
        current["saunas"].append({
            "name": sauna.get("name", "Unknown"),
            "current_seats": current_seats,
            "max_seats": max_seats,
            "occupancy_percent": round((current_seats / max_seats) * 100, 1) if max_seats > 0 else 0,
            "capacity_message": sauna.get("capacity_message", "")
        })

    # Add weather data if available
    if weather:
        current["weather"] = weather

    with open(CURRENT_FILE, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)


def calculate_statistics(records):
    """Calculate hourly and weekday statistics and save them."""
    from collections import defaultdict

    # Group by hour (overall) and by weekday+hour
    hourly_stats = defaultdict(lambda: defaultdict(list))
    weekday_hourly_stats = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    # Weekday names (0=Monday, 6=Sunday)
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    for record in records:
        try:
            dt = datetime.fromisoformat(record["timestamp"])
            hour = dt.hour
            weekday = weekday_names[dt.weekday()]
            name = record["name"]
            occupancy = record["occupancy_percent"]

            hourly_stats[hour][name].append(occupancy)
            weekday_hourly_stats[weekday][hour][name].append(occupancy)
        except (KeyError, ValueError):
            continue

    # Calculate overall hourly averages
    stats = {
        "by_hour": {},
        "by_weekday": {}
    }

    for hour in range(24):
        stats["by_hour"][hour] = {}
        for name in hourly_stats[hour]:
            values = hourly_stats[hour][name]
            if values:
                stats["by_hour"][hour][name] = {
                    "avg": round(sum(values) / len(values), 1),
                    "min": round(min(values), 1),
                    "max": round(max(values), 1),
                    "count": len(values)
                }

    # Calculate weekday-specific hourly averages
    for weekday in weekday_names:
        stats["by_weekday"][weekday] = {}
        for hour in range(24):
            stats["by_weekday"][weekday][hour] = {}
            for name in weekday_hourly_stats[weekday][hour]:
                values = weekday_hourly_stats[weekday][hour][name]
                if values:
                    stats["by_weekday"][weekday][hour][name] = {
                        "avg": round(sum(values) / len(values), 1),
                        "min": round(min(values), 1),
                        "max": round(max(values), 1),
                        "count": len(values)
                    }

    stats_file = DATA_DIR / "statistics.json"
    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)


def calculate_weather_statistics(records):
    """Calculate weather-occupancy correlation statistics."""
    from collections import defaultdict

    # Filter records that have weather data and are for main sauna
    weather_records = [r for r in records if r.get("weather") and r.get("name") == "Sauna"]

    if len(weather_records) < 5:
        print("Not enough weather data for statistics yet")
        return

    # Temperature buckets: <5, 5-10, 10-15, 15-20, 20-25, 25+
    temp_buckets = defaultdict(list)
    # Weather conditions
    rainy_occupancies = []
    sunny_occupancies = []
    cloudy_occupancies = []
    # Humidity buckets
    humidity_buckets = defaultdict(list)

    for r in weather_records:
        weather = r["weather"]
        occupancy = r["occupancy_percent"]
        temp = weather.get("temperature")

        if temp is not None:
            if temp < 5:
                temp_buckets["< 5°C"].append(occupancy)
            elif temp < 10:
                temp_buckets["5-10°C"].append(occupancy)
            elif temp < 15:
                temp_buckets["10-15°C"].append(occupancy)
            elif temp < 20:
                temp_buckets["15-20°C"].append(occupancy)
            elif temp < 25:
                temp_buckets["20-25°C"].append(occupancy)
            else:
                temp_buckets["> 25°C"].append(occupancy)

        # Weather conditions
        if weather.get("is_rainy"):
            rainy_occupancies.append(occupancy)
        if weather.get("is_sunny"):
            sunny_occupancies.append(occupancy)
        cloud_cover = weather.get("cloud_cover", 0)
        if cloud_cover > 70:
            cloudy_occupancies.append(occupancy)

        # Humidity
        humidity = weather.get("humidity")
        if humidity is not None:
            if humidity < 50:
                humidity_buckets["< 50%"].append(occupancy)
            elif humidity < 70:
                humidity_buckets["50-70%"].append(occupancy)
            else:
                humidity_buckets["> 70%"].append(occupancy)

    # Calculate averages
    def calc_stats(values):
        if not values:
            return None
        return {
            "avg": round(sum(values) / len(values), 1),
            "min": round(min(values), 1),
            "max": round(max(values), 1),
            "count": len(values)
        }

    # Overall average for comparison
    all_occupancies = [r["occupancy_percent"] for r in weather_records]
    overall_avg = sum(all_occupancies) / len(all_occupancies) if all_occupancies else 0

    stats = {
        "overall_avg": round(overall_avg, 1),
        "total_records": len(weather_records),
        "by_temperature": {},
        "by_condition": {},
        "by_humidity": {}
    }

    # Temperature stats (ordered)
    temp_order = ["< 5°C", "5-10°C", "10-15°C", "15-20°C", "20-25°C", "> 25°C"]
    for bucket in temp_order:
        if temp_buckets[bucket]:
            stats["by_temperature"][bucket] = calc_stats(temp_buckets[bucket])

    # Condition stats
    if rainy_occupancies:
        stats["by_condition"]["rainy"] = calc_stats(rainy_occupancies)
    if sunny_occupancies:
        stats["by_condition"]["sunny"] = calc_stats(sunny_occupancies)
    if cloudy_occupancies:
        stats["by_condition"]["cloudy"] = calc_stats(cloudy_occupancies)

    # Humidity stats
    humidity_order = ["< 50%", "50-70%", "> 70%"]
    for bucket in humidity_order:
        if humidity_buckets[bucket]:
            stats["by_humidity"][bucket] = calc_stats(humidity_buckets[bucket])

    with open(WEATHER_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Weather statistics calculated from {len(weather_records)} records")


def log_occupancy(saunas, weather=None):
    """Log occupancy data to CSV and JSON files."""
    if not saunas:
        return

    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now(ZoneInfo("Europe/Zurich")).isoformat()

    # Save current state
    save_current(saunas, timestamp, weather)

    # Load existing records
    records = load_existing_data()

    # Append new records
    for sauna in saunas:
        current_seats = sauna.get("current_seats", 0)
        max_seats = sauna.get("max_seats", 1)
        occupancy_pct = round((current_seats / max_seats) * 100, 1) if max_seats > 0 else 0

        record = {
            "timestamp": timestamp,
            "name": sauna.get("name", "Unknown"),
            "current_seats": current_seats,
            "max_seats": max_seats,
            "occupancy_percent": occupancy_pct,
            "capacity_message": sauna.get("capacity_message", "")
        }
        # Add weather data to each record
        if weather:
            record["weather"] = weather
        records.append(record)

    # Save JSON
    save_json_data(records)

    # Calculate and save statistics
    calculate_statistics(records)
    calculate_weather_statistics(records)

    # Also save to CSV for compatibility
    csv_exists = CSV_FILE.exists()
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not csv_exists:
            writer.writerow(["timestamp", "name", "current_seats", "max_seats", "occupancy_percent", "capacity_message"])
        for sauna in saunas:
            current_seats = sauna.get("current_seats", 0)
            max_seats = sauna.get("max_seats", 1)
            writer.writerow([
                timestamp,
                sauna.get("name", "Unknown"),
                current_seats,
                max_seats,
                round((current_seats / max_seats) * 100, 1) if max_seats > 0 else 0,
                sauna.get("capacity_message", "")
            ])

    print(f"[{timestamp}] Logged {len(saunas)} sauna(s)")


def main():
    """Main function to fetch and log occupancy."""
    print("Fetching sauna occupancy data...")
    saunas = fetch_occupancy()

    print("Fetching weather data for Bern...")
    weather = fetch_weather()

    if saunas:
        log_occupancy(saunas, weather)
        for sauna in saunas:
            current = sauna.get("current_seats", 0)
            max_seats = sauna.get("max_seats", 1)
            pct = round((current / max_seats) * 100, 1) if max_seats > 0 else 0
            print(f"  {sauna.get('name')}: {current}/{max_seats} ({pct}%) - {sauna.get('capacity_message')}")

        if weather:
            print(f"  Weather: {weather.get('temperature')}°C, {weather.get('weather_description')}")
    else:
        print("Failed to fetch occupancy data")


if __name__ == "__main__":
    main()
