# Sentinel

Sentinel is a Python script I built to fetch near-Earth asteroid data from NASA's NeoWs API. It uses Google's Gemini AI to analyze the data, give each asteroid a risk score (1-10), and write a short summary of how dangerous it is.

I originally had a web interface for this, but I realized it was better to keep things simple and just export the data so I can plug it straight into Power BI for making dashboards!

---

## What It Does

- Pulls asteroid data from NASA for any date range you want.
- Filters out asteroids that aren't coming very close to Earth.
- Uses Gemini AI to look at the speed, size, and distance, and grades the risk from 1 to 10.
- Saves the data to an SQLite database AND spits out a CSV file (`asteroids_data.csv`) that's ready for Power BI.
- Also saves a readable text report in markdown format.

---

## How to Set It Up

**1. Clone the project**
```bash
git clone https://github.com/JayceJimmerson/Sentinel.git
cd Sentinel
```

**2. Make a virtual environment (so it doesn't mess with your other Python stuff)**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**3. Install what it needs**
```bash
pip install -r requirements.txt
```

**4. Get API Keys**
You need two free API keys for this to work:
- NASA API key: Get it at [api.nasa.gov](https://api.nasa.gov/)
- Gemini API key: Get it at [Google AI Studio](https://aistudio.google.com/)

Rename the `.env.example` file to `.env` and paste your keys in there:
```env
NASA_API_KEY=your_nasa_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## How to Use It

Just run the script in your terminal!

```bash
# Get data for the next 7 days
python sentinel.py

# Get data for the next 14 days
python sentinel.py --days 14
```

When it finishes, you'll see a new report in the `outputs/` folder, and an `asteroids_data.csv` file that you can drag right into Power BI.

---

## Why I Built This

I'm learning more about Python, APIs, and data analysis. This project helped me figure out how to:
- Connect to REST APIs (NASA) and handle JSON data.
- Use AI SDKs (Google Gemini) to process information.
- Use SQLite and CSVs to store data for visualization tools like Power BI.
- Manage my code with Git.

Feel free to check out the code!
