import streamlit as st
import pandas as pd
from datetime import date, timedelta
import db
import sentinel
import google.generativeai as genai
import os

# Setup page config
st.set_page_config(page_title="Sentinel — Near-Earth Object Tracker", page_icon="☄️", layout="wide")

# Custom CSS for high-end aesthetics
st.markdown("""
<style>
    /* Premium visual styling */
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global font override */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Header fonts override */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.5px;
    }

    /* Custom Metric Cards (Glassmorphism) */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(28, 28, 56, 0.45) 0%, rgba(15, 15, 32, 0.65) 100%) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 14px !important;
        padding: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2) !important;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-3px) !important;
        border-color: rgba(0, 230, 118, 0.25) !important;
        box-shadow: 0 12px 40px rgba(0, 230, 118, 0.08) !important;
    }
    
    div[data-testid="stMetricLabel"] > div {
        color: #8c8ca8 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-weight: 600 !important;
    }
    
    div[data-testid="stMetricValue"] > div {
        color: #ffffff !important;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        margin-top: 4px !important;
    }

    /* Expander styling override */
    div[data-testid="stExpander"] {
        background: rgba(22, 22, 45, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
        margin-bottom: 14px !important;
        transition: all 0.2s ease !important;
        backdrop-filter: blur(5px) !important;
    }
    
    div[data-testid="stExpander"]:hover {
        border-color: rgba(255, 255, 255, 0.15) !important;
        background: rgba(22, 22, 45, 0.45) !important;
    }

    /* Tab styling */
    button[data-baseweb="tab"] {
        font-size: 1rem !important;
        font-weight: 500 !important;
        color: #8c8ca8 !important;
        padding: 12px 20px !important;
        transition: all 0.2s ease !important;
    }
    
    button[aria-selected="true"] {
        color: #00e676 !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# Make sure DB is initialized
db.init_db()

# Configure Gemini with a robust key validator
if sentinel.GEMINI_API_KEY and not sentinel.GEMINI_API_KEY.endswith("_here"):
    genai.configure(api_key=sentinel.GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(sentinel.GEMINI_MODEL)
else:
    st.error("⚠️ **Missing or Invalid Gemini API Key!**")
    st.info("""
    Sentinel requires a Google Gemini API key to generate asteroid risk narratives.
    
    **How to fix:**
    1. Open or create the `.env` file in your project folder.
    2. Add your Gemini API key:
       ```env
       GEMINI_API_KEY=your_actual_key_here
       ```
    3. You can get a free API key at [Google AI Studio](https://aistudio.google.com/).
    """)
    st.stop()


def get_risk_color(score):
    if score >= 7: return "#ff1744" # Neon Red
    if score >= 4: return "#ffb300" # Orange/Amber
    return "#00e676" # Neon Green


def draw_risk_bar(score, color):
    pct = score * 10
    return f"""
    <div style="margin-top: 8px; margin-bottom: 12px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <span style="font-size: 0.85rem; color: #8c8ca8; font-weight: 500;">Threat Level</span>
            <span style="font-size: 0.95rem; color: {color}; font-weight: 700;">{score}/10</span>
        </div>
        <div style="background-color: rgba(255,255,255,0.08); border-radius: 6px; width: 100%; height: 8px; overflow: hidden;">
            <div style="background: linear-gradient(90deg, {color}88, {color}); width: {pct}%; height: 100%; border-radius: 6px; box-shadow: 0 0 10px {color}77;"></div>
        </div>
    </div>
    """


# ─── HEADER BANNER ───────────────────────────────────────────────────────────
st.markdown("""
<div style="background: linear-gradient(135deg, #181832 0%, #0c0c16 100%); padding: 30px; border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.08); margin-bottom: 25px; box-shadow: 0 8px 32px 0 rgba(0,0,0,0.3);">
    <h1 style="color: #ffffff; margin: 0; font-size: 2.8rem; font-weight: 700; display: flex; align-items: center; gap: 12px;">☄️ SENTINEL</h1>
    <p style="color: #8c8ca8; margin: 8px 0 0 0; font-size: 1.1rem; font-weight: 400; line-height: 1.5;">Near-Earth Object Tracking & Threat Assessment powered by NASA JPL and Google Gemini AI.</p>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR: FETCH NEW DATA ───────────────────────────────────────────────
st.sidebar.header("Fetch New Data")
with st.sidebar.form("fetch_form"):
    start_date = st.date_input("Start Date", date.today())
    days = st.number_input("Days to Look Ahead", min_value=1, max_value=60, value=7)
    max_dist_km = st.number_input("Max Distance (km)", min_value=100000, value=5000000, step=100000)
    
    submit = st.form_submit_button("Run Space Analysis", type="primary")

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
                assessment = {"score": 1, "narrative": f"Error generating assessment: {e}"}
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
    st.metric("Total Objects Tracked", f"{total_asteroids:,}")
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
st.subheader("📊 Space Registry & Historical Reports")

reports = db.get_reports()
if not reports:
    st.info("No reports generated yet. Use the sidebar on the left to run an analysis and build your space registry!")
else:
    # Build a dictionary for easy selectbox rendering
    report_options = {r["id"]: f"Report #{r['id']} ({r['start_date']} to {r['end_date']}) — {r['object_count']} objects" for r in reports}
    selected_report_id = st.selectbox("Select a report to inspect:", options=list(report_options.keys()), format_func=lambda x: report_options[x])
    
    if selected_report_id:
        report, asteroids = db.get_report(selected_report_id)
        
        st.markdown(f"### Details for Report #{report['id']}")
        st.markdown(f"📅 **Date Range:** {report['start_date']} to {report['end_date']} | 🛰️ **Max Query Distance:** {report['max_distance_km']:,.0f} km")
        
        # Tabs for detailed assessments vs interactive charts
        tab1, tab2 = st.tabs(["📋 Detailed Assessments", "📈 Visual Analytics"])
        
        with tab1:
            for ast in asteroids:
                score = ast['risk_score']
                color = get_risk_color(score)
                emoji = "🔴" if score >= 7 else "🟡" if score >= 4 else "🟢"
                
                with st.expander(f"{emoji} {ast['name']} — Miss Distance: {ast['miss_distance_km']:,.0f} km (Risk: {score}/10)"):
                    c1, c2 = st.columns([2, 3])
                    with c1:
                        st.markdown("##### Technical Specifications")
                        st.markdown(f"📅 **Approach Date:** `{ast['approach_date']}`")
                        st.markdown(f"🚀 **Relative Velocity:** `{ast['velocity_kph']:,.0f} km/h`")
                        st.markdown(f"📏 **Estimated Diameter:** `{ast['diameter_min_m']:.1f}m – {ast['diameter_max_m']:.1f}m`")
                        
                        hazardous_val = "Yes" if ast['hazardous'] else "No"
                        hazard_color = "red" if ast['hazardous'] else "green"
                        st.markdown(f"🚨 **NASA Hazard Flag:** :{hazard_color}[{hazardous_val}]")
                        
                        # Draw beautiful threat meter
                        st.markdown(draw_risk_bar(score, color), unsafe_allow_html=True)
                    
                    with c2:
                        st.markdown("##### 🤖 Gemini AI Threat Assessment")
                        st.info(ast['narrative'])
        
        with tab2:
            if not asteroids:
                st.info("No objects in this report to analyze.")
            else:
                # Convert asteroids to a Pandas DataFrame
                df = pd.DataFrame([dict(a) for a in asteroids])
                
                # Setup columns for the visualizations
                chart_col1, chart_col2 = st.columns(2)
                
                with chart_col1:
                    st.markdown("##### ☄️ Threat Distribution: Diameter vs. Miss Distance")
                    st.markdown("Plots asteroid max size against proximity. Larger, closer objects represent higher risk.")
                    
                    # Prepare dataframe for charting
                    chart_df = df.copy()
                    chart_df["Diameter (m)"] = chart_df["diameter_max_m"]
                    chart_df["Miss Distance (million km)"] = chart_df["miss_distance_km"] / 1_000_000
                    chart_df["Risk Score"] = chart_df["risk_score"]
                    
                    # Display beautiful Streamlit scatter chart
                    st.scatter_chart(
                        data=chart_df,
                        x="Miss Distance (million km)",
                        y="Diameter (m)",
                        color="Risk Score",
                        size="Risk Score",
                        use_container_width=True
                    )
                    
                with chart_col2:
                    st.markdown("##### 📊 Risk Rating Distribution")
                    st.markdown("Count of objects analyzed grouped by their severity levels.")
                    
                    # Calculate counts for each risk category
                    risk_counts = pd.DataFrame({
                        "Risk Severity": ["Low (1-3)", "Moderate (4-6)", "Elevated (7-8)", "High (9-10)"],
                        "Count": [
                            len(chart_df[chart_df["risk_score"] <= 3]),
                            len(chart_df[(chart_df["risk_score"] >= 4) & (chart_df["risk_score"] <= 6)]),
                            len(chart_df[(chart_df["risk_score"] >= 7) & (chart_df["risk_score"] <= 8)]),
                            len(chart_df[chart_df["risk_score"] >= 9])
                        ]
                    })
                    # Exclude categories with 0 count to keep chart clean
                    risk_counts = risk_counts[risk_counts["Count"] > 0]
                    
                    # Display beautiful Streamlit bar chart
                    st.bar_chart(
                        data=risk_counts,
                        x="Risk Severity",
                        y="Count",
                        color="#00e676",
                        use_container_width=True
                    )
                
                st.markdown("##### 📋 Technical Registry")
                # Show neat clean table of technical details
                registry_df = df[["name", "approach_date", "miss_distance_km", "velocity_kph", "diameter_max_m", "risk_score"]].copy()
                registry_df.columns = ["Object Name", "Approach Date", "Miss Distance (km)", "Velocity (km/h)", "Diameter Max (m)", "Gemini Risk Score"]
                st.dataframe(
                    registry_df.style.format({
                        "Miss Distance (km)": "{:,.0f}",
                        "Velocity (km/h)": "{:,.0f}",
                        "Diameter Max (m)": "{:.1f}",
                    }),
                    use_container_width=True,
                    hide_index=True
                )

