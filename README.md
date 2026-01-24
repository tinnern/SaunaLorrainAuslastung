# Sauna Lorraine Occupancy Tracker

Tracks and logs occupancy data from the Lorrainebad sauna in Bern.

## Quick Start

```bash
pip install -r requirements.txt
python scraper.py
```

Data is logged to `occupancy_log.csv` with columns:
- `timestamp` - ISO format datetime
- `name` - Sauna name
- `current_seats` - Currently occupied seats
- `max_seats` - Maximum capacity
- `occupancy_percent` - Calculated percentage
- `capacity_message` - Status message from the API

---

## Running Continuously

### Option 1: Cron (macOS/Linux) - Recommended for local

Run every 15 minutes:

```bash
# Edit crontab
crontab -e

# Add this line (adjust path):
*/15 * * * * cd /Users/slin/Documents/Privat/SaunaLorrainAuslastung && /usr/bin/python3 scraper.py >> cron.log 2>&1
```

### Option 2: macOS launchd (runs even after reboot)

1. Create `~/Library/LaunchAgents/ch.saunalorrainebad.tracker.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ch.saunalorrainebad.tracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/slin/Documents/Privat/SaunaLorrainAuslastung/scraper.py</string>
    </array>
    <key>StartInterval</key>
    <integer>900</integer>
    <key>WorkingDirectory</key>
    <string>/Users/slin/Documents/Privat/SaunaLorrainAuslastung</string>
    <key>StandardOutPath</key>
    <string>/Users/slin/Documents/Privat/SaunaLorrainAuslastung/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/slin/Documents/Privat/SaunaLorrainAuslastung/launchd.log</string>
</dict>
</plist>
```

2. Load it:
```bash
launchctl load ~/Library/LaunchAgents/ch.saunalorrainebad.tracker.plist
```

3. To stop:
```bash
launchctl unload ~/Library/LaunchAgents/ch.saunalorrainebad.tracker.plist
```

### Option 3: Cloud deployment (24/7, no local machine needed)

**Free/cheap options:**

1. **Railway.app** - Free tier, easy Python deployment
2. **Render.com** - Free cron jobs
3. **PythonAnywhere** - Free tier includes scheduled tasks
4. **GitHub Actions** - Free scheduled workflows

Example GitHub Actions workflow (`.github/workflows/scrape.yml`):

```yaml
name: Scrape Sauna Occupancy
on:
  schedule:
    - cron: '*/15 * * * *'  # Every 15 minutes
  workflow_dispatch:

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python scraper.py
      - name: Commit data
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add occupancy_log.csv
          git diff --staged --quiet || git commit -m "Update occupancy data"
          git push
```

---

## Viewing the Data

The CSV can be opened in Excel, Google Sheets, or analyzed with Python/pandas:

```python
import pandas as pd
df = pd.read_csv("occupancy_log.csv", parse_dates=["timestamp"])
print(df.groupby(df["timestamp"].dt.hour)["occupancy_percent"].mean())
```
