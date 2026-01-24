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

import requests

API_URL = "https://lorauna.app/api"
GRAPHQL_QUERY = "{ allSaunas { name, current_seats, max_seats, capacity_message } }"
DATA_FILE = Path(__file__).parent / "occupancy_log.csv"


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


def log_occupancy(saunas):
    """Log occupancy data to CSV file."""
    if not saunas:
        return

    timestamp = datetime.now().isoformat()
    file_exists = DATA_FILE.exists()

    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header if file is new
        if not file_exists:
            writer.writerow([
                "timestamp",
                "name",
                "current_seats",
                "max_seats",
                "occupancy_percent",
                "capacity_message"
            ])

        for sauna in saunas:
            current = sauna.get("current_seats", 0)
            max_seats = sauna.get("max_seats", 1)
            occupancy_pct = round((current / max_seats) * 100, 1) if max_seats > 0 else 0

            writer.writerow([
                timestamp,
                sauna.get("name", "Unknown"),
                current,
                max_seats,
                occupancy_pct,
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
