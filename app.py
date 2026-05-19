import streamlit as st
import pandas as pd
from datetime import date, timedelta
import db
import sentinel
import google.generativeai as genai
import os

# Setup page config
st.set_page_config(page_title="Sentinel", page_icon="☄️", layout="wide")

# Custom CSS for aesthetics
st.markdown("""
<style>
    .risk-low { color: #00e676; font-weight: bold; }
    .risk-mid { color: #ffea00; font-weight: bold; }
    .risk-high { color: #ff1744; font-weight: bold; }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Make sure DB is initialized
db.init_db()

# Configure Gemini
if sentinel.GEMINI_API_KEY:
    genai.configure(api_key=sentinel.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(sentinel.GEMINI_MODEL)
else:
    st.error("Please set GEMINI_API_KEY in your .env file!")
    st.stop()


def risk_color(score):
    if score >= 7: return "red"
    if score >= 4: return "orange"
    return "green"


st.title("☄️ Sentinel")
st.markdown("Monitor near-Earth objects using NASA's JPL CAD API and Google Gemini AI.")

# ─── SIDEBAR: FETCH NEW DATA ───────────────────────────────────────────────
st.sidebar.header("Fetch New Data")
with st.sidebar.form("fetch_form"):
    start_date = st.date_input("Start Date", date.today())
    days = st.number_input("Days to Look Ahead", min_value=1, max_value=60, value=7)
    max_dist_km = st.number_input("Max Distance (km)", min_value=100000, value=5000000, step=100000)
    
    submit = st.form_submit_button("Run Analysis", type="primary")

if submit:
    end_date = start_date + timedelta(days=days - 1)
    
    with st.spinner(f"Fetching objects from JPL CAD API ({start_date} to {end_date})..."):
        try:
            asteroids = sentinel.fetch_neos(start_date, end_date, max_dist_km)
        except Exception as e:
            st.error(f"Failed to fetch data: {e}")
            asteroids = []

    if not asteroids:
        st.info("No asteroids found in that range matching your criteria.")
    else:
        st.success(f"Found {len(asteroids)} objects! Generating Gemini AI assessments...")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        assessments = []
        for i, ast in enumerate(asteroids):
            status_text.text(f"Analyzing {ast['name']} ({i+1}/{len(asteroids)})...")
            try:
                assessment = sentinel.generate_assessment(gemini_model, ast)
            except Exception as e:
                assessment = {"score": 0, "narrative": f"Error generating assessment: {e}"}
            assessments.append(assessment)
            progress_bar.progress((i + 1) / len(asteroids))
            
        status_text.text("Saving report to database...")
        report_id = db.save_report(str(start_date), str(end_date), max_dist_km, sentinel.GEMINI_MODEL, asteroids, assessments)
        
        # Save markdown report as well
        sentinel.save_report(start_date, end_date, max_dist_km, asteroids, assessments)
        
        status_text.text("Done!")
        st.balloons()
        st.rerun()

# ─── MAIN: DASHBOARD ───────────────────────────────────────────────────────
total_asteroids = db.get_total_asteroid_count()
next_approach = db.get_next_approach()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Objects Tracked", total_asteroids)
with col2:
    if next_approach:
        st.metric("Next Close Approach", next_approach["name"], f"{next_approach['approach_date']}")
    else:
        st.metric("Next Close Approach", "None")
with col3:
    if next_approach:
        score = next_approach["risk_score"]
        st.metric("Highest Risk Score", f"{score}/10")
    else:
        st.metric("Highest Risk Score", "N/A")

st.markdown("---")
st.subheader("Historical Reports")

reports = db.get_reports()
if not reports:
    st.info("No reports generated yet. Use the sidebar to run an analysis.")
else:
    # Build a dictionary for easy selectbox rendering
    report_options = {r["id"]: f"Report #{r['id']} ({r['start_date']} to {r['end_date']}) - {r['object_count']} objects" for r in reports}
    selected_report_id = st.selectbox("Select a report to view details:", options=list(report_options.keys()), format_func=lambda x: report_options[x])
    
    if selected_report_id:
        report, asteroids = db.get_report(selected_report_id)
        
        st.markdown(f"### Details for Report #{report['id']}")
        st.markdown(f"**Date Range:** {report['start_date']} to {report['end_date']} | **Max Distance:** {report['max_distance_km']:,.0f} km")
        
        for ast in asteroids:
            score = ast['risk_score']
            emoji = "🔴" if score >= 7 else "🟡" if score >= 4 else "🟢"
            
            with st.expander(f"{emoji} {ast['name']} - Miss Distance: {ast['miss_distance_km']:,.0f} km (Score: {score}/10)"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"**Approach Date:** {ast['approach_date']}")
                    st.markdown(f"**Velocity:** {ast['velocity_kph']:,.0f} km/h")
                    st.markdown(f"**Diameter:** {ast['diameter_min_m']:.1f}m - {ast['diameter_max_m']:.1f}m")
                    st.markdown(f"**NASA Hazard Flag:** {'Yes' if ast['hazardous'] else 'No'}")
                    
                    color = risk_color(score)
                    st.markdown(f"**Risk Score:** :{color}[{score}/10]")
                
                with c2:
                    st.markdown("**AI Risk Assessment:**")
                    st.info(ast['narrative'])
