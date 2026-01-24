# Sauna Lorrainebad Auslastung

Live occupancy tracker for the [Lorrainebad Sauna](https://saunalorrainebad.ch/) in Bern.

## Live Dashboard

**https://real-slin-shady.github.io/SaunaLorrainAuslastung/**

The dashboard shows:
- Current occupancy (live)
- Typical occupancy by hour (average over collected data)
- Last 24 hours history
- Best times to visit (lowest average occupancy)

## How It Works

```
GitHub Actions (every 15 min)
        |
        v
  Scrapes API at lorauna.app
        |
        v
  Saves data to /data folder
        |
        v
  GitHub Pages serves dashboard
```

- **Scraper**: Runs automatically via GitHub Actions every 15 minutes
- **Data**: Stored in `data/` folder (JSON + CSV)
- **Dashboard**: Static HTML/JS hosted on GitHub Pages

## Data Collected

The API provides:
- `current_seats` - Currently occupied seats
- `max_seats` - Maximum capacity (40)
- `capacity_message` - Status in Berndütsch + English

Data is stored in:
- `data/current.json` - Latest reading
- `data/occupancy_log.json` - Full history
- `data/statistics.json` - Hourly averages
- `data/occupancy_log.csv` - CSV backup

## Tech Stack

- Python (scraper)
- Chart.js (charts)
- GitHub Actions (scheduling)
- GitHub Pages (hosting)

## Note

The API returns two saunas ("Sauna" and "Sauna rechts"). Currently only "Sauna" is displayed on the dashboard, but both are tracked in the data files for future analysis.
