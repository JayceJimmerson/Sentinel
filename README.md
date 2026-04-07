# Sentinel

Sentinel fetches near-Earth asteroid close-approach data from NASA's NeoWs API and uses Claude AI to generate a plain-English risk narrative and 1–10 risk score for each object. Results are saved to a local SQLite database and viewable through a Flask web UI.

---

## Features

- Fetches asteroid data for any date range (chains NASA's 7-day API windows automatically)
- Filters by maximum miss distance
- Uses Claude to score each asteroid on a 1–10 risk scale with a plain-English narrative
- Saves all reports and asteroid data to a local SQLite database
- Flask web UI to browse and review past reports

---

## Requirements

- Python 3.12+
- A [NASA API key](https://api.nasa.gov/) (free)
- An [Anthropic API key](https://console.anthropic.com/)

---

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/JayceJimmerson/Sentinel
cd Sentinel
```

**2. Create and activate a virtual environment**

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Copy the example below into a file named `.env` in the project root:

```env
NASA_API_KEY=your_nasa_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

> `.env` is git-ignored and will never be committed.

---

## Usage

### CLI — Generate a report

```bash
python sentinel.py                              # next 7 days, within 5,000,000 km
python sentinel.py --days 14                    # next 14 days
python sentinel.py --days 30 --start 2026-05-01 # 30 days starting May 1
python sentinel.py --days 7 --max-distance 1000000  # tighter distance filter
```

| Flag | Default | Description |
|---|---|---|
| `--days N` | `7` | Number of days to look ahead |
| `--start YYYY-MM-DD` | today | Start date for the window |
| `--max-distance KM` | `5000000` | Only include objects within this many km |

Reports are saved as Markdown files in the `outputs/` folder and stored in the database.

### Web UI — Browse reports

```bash
python app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## Risk Score Guide

Claude scores each asteroid 1–10 based on the **combination** of miss distance, velocity, and diameter — not just NASA's binary hazard flag.

| Score | Level | Meaning |
|---|---|---|
| 1–2 | Negligible | Very distant, tiny, or slow |
| 3–4 | Low | Distant or small, no real concern |
| 5–6 | Moderate | Closer approach or larger object, worth noting |
| 7–8 | Elevated | Combination of close, fast, and/or large |
| 9–10 | High | Very close, large, and/or fast — genuinely notable |

---

## Project Structure

```
Sentinel/
├── sentinel.py       # CLI entry point — fetches data, calls Claude, saves reports
├── app.py            # Flask web UI
├── db.py             # SQLite persistence layer
├── requirements.txt  # Python dependencies
├── templates/
│   ├── base.html     # Shared layout and styles
│   ├── index.html    # Report list page
│   └── report.html   # Individual report detail page
└── outputs/          # Generated Markdown reports (git-ignored)
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | NASA NeoWs API calls |
| `anthropic` | Claude AI risk assessments |
| `python-dotenv` | Load API keys from `.env` |
| `flask` | Web UI server |
