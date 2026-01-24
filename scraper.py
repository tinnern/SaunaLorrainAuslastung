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


def save_current(saunas, timestamp):
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


def log_occupancy(saunas):
    """Log occupancy data to CSV and JSON files."""
    if not saunas:
        return

    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now(ZoneInfo("Europe/Zurich")).isoformat()

    # Save current state
    save_current(saunas, timestamp)

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
        records.append(record)

    # Save JSON
    save_json_data(records)

    # Calculate and save statistics
    calculate_statistics(records)

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

    if saunas:
        log_occupancy(saunas)
        for sauna in saunas:
            current = sauna.get("current_seats", 0)
            max_seats = sauna.get("max_seats", 1)
            pct = round((current / max_seats) * 100, 1) if max_seats > 0 else 0
            print(f"  {sauna.get('name')}: {current}/{max_seats} ({pct}%) - {sauna.get('capacity_message')}")
    else:
        print("Failed to fetch occupancy data")


if __name__ == "__main__":
    main()
