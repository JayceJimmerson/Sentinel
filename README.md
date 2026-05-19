# Sentinel

Sentinel is an interactive space-registry and risk-profile dashboard that tracks near-Earth objects (NEOs). It pulls real-time close-approach data directly from NASA's JPL API and leverages Google's Gemini AI to generate plain-English risk summaries and visual threat-severity scores (1-10).

The entire app is built in **Python** and packaged in a stunning, high-end **Streamlit** dashboard, making it easy to track space telemetry and explore historical database records!

---

## Key Features

- **Interactive Telemetry Dashboard:** View close-approach data including approach date, velocity (km/h), max/min estimated diameter (meters), and miss distance (km).
- **Gemini AI Risk Assessment:** Integrates Google's `gemini-2.5-flash` model to analyze complex aerospace metrics and write intuitive, factual threat summaries alongside a curated 1-10 threat rating.
- **Glassmorphic UI Elements:** Styled with curated typography (Space Grotesk & Inter), visual linear-gradient threat meters, and a clean, technical dark mode.
- **Space Analytics & Visualization:** Native charts plotting maximum diameter vs. proximity (scatter chart) and threat-level distribution frequency (bar chart).
- **Persistent Local Database:** Leverages SQLite to store every generated report and asteroid assessment so you can build and inspect your own space telemetry history.
- **Public NASA JPL CAD API:** Swapped from NeoWs to the open JPL Close-Approach Data API to completely eliminate NASA API key friction for a zero-friction startup.

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

**4. Get an API Key**
You need one free API key for this to work:
- Gemini API key: Get it at [Google AI Studio](https://aistudio.google.com/)
(Note: The NASA JPL endpoint is completely public and doesn't require a key!)

Rename the `.env.example` file to `.env` and paste your key in there:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

---

## How to Use It

Start the Streamlit dashboard by running this command in your terminal:

```bash
streamlit run app.py
```

This will automatically open the Sentinel dashboard in your web browser. 

From the sidebar on the left, you can:
1. Select a start date and how many days to look ahead.
2. Hit **Run Analysis**.
3. Watch as it fetches data from NASA and uses Gemini AI to analyze each asteroid in real-time!

You can also use the main dashboard to select and view reports you've run in the past.
