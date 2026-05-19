# Sentinel

Sentinel is a Python web application that fetches near-Earth asteroid data from NASA's JPL Close-Approach Data API and uses Google's Gemini AI to analyze the data. It gives each asteroid a risk score (1-10) and writes a short summary of how dangerous it is.

The entire app is built with **Streamlit**, giving it a beautiful, interactive dashboard where you can browse past asteroid assessments and generate new ones!

---

## What It Does

- Pulls asteroid data from NASA for any date range you want (no NASA API key required!).
- Uses Gemini AI to look at the speed, size, and distance, and grades the risk from 1 to 10.
- Saves all reports to a local SQLite database so you can view your history.
- Presents everything in a clean, modern web interface.

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
