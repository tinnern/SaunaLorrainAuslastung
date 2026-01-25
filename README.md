# Sauna Lorrainebad Auslastung

Live occupancy tracker for the [Lorrainebad Sauna](https://saunalorrainebad.ch/) in Bern.

## Live Dashboard

**https://real-slin-shady.github.io/SaunaLorrainAuslastung/**

The dashboard shows:
- Current occupancy (live)
- Current weather in Bern
- Typical occupancy by hour per weekday
- Last 24 hours history
- Best times to visit (lowest average occupancy)
- Weather & occupancy correlation (temperature, rain, etc.)

## Opening Hours

| Day | Hours |
|-----|-------|
| Monday (FLINTA*) | 10:00 - 21:30 |
| Tuesday | 10:00 - 21:30 |
| Wednesday | Closed |
| Thursday | 10:00 - 21:30 |
| Friday | 10:00 - 21:30 |
| Saturday | 09:00 - 21:30 |
| Sunday | 09:00 - 21:30 |

## How It Works

```
cron-job.org (every 15 min)
        |
        v
Triggers GitHub Actions
        |
        v
    Scraper
   /       \
  v         v
lorauna.app   Open-Meteo
(occupancy)   (weather)
   \       /
    v     v
Saves data to /data folder
        |
        v
GitHub Pages serves dashboard
```

- **Scraper**: Triggered every 15 minutes via [cron-job.org](https://cron-job.org) → GitHub Actions
- **Data**: Stored in `data/` folder (JSON + CSV)
- **Weather**: Fetched from Open-Meteo API for Bern (free, no API key)
- **Dashboard**: Static HTML/JS hosted on GitHub Pages

## Data Collected

**Sauna data** from lorauna.app API:
- `current_seats` - Currently occupied seats
- `max_seats` - Maximum capacity (40)
- `capacity_message` - Status in Berndeutsch + English

**Weather data** from Open-Meteo API (Bern):
- Temperature & apparent temperature
- Precipitation & humidity
- Weather conditions (sunny, cloudy, rainy, etc.)

Data is stored in:
- `data/current.json` - Latest reading (sauna + weather)
- `data/occupancy_log.json` - Full history with weather
- `data/statistics.json` - Hourly/weekday averages
- `data/weather_stats.json` - Weather-occupancy correlations
- `data/occupancy_log.csv` - CSV backup

## Tech Stack

- Python (scraper)
- Chart.js (charts)
- Open-Meteo API (weather data)
- GitHub Actions (workflow)
- GitHub Pages (hosting)
- cron-job.org (reliable scheduling)

## Note

The API returns two saunas ("Sauna" and "Sauna rechts"). Currently only "Sauna" is displayed on the dashboard, but both are tracked in the data files for future analysis.
