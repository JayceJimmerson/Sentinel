"""
app.py — Flask web UI for Sentinel.

Run:  python app.py
      flask --app app run --debug
"""

from flask import Flask, render_template, abort
import db

app = Flask(__name__)
db.init_db()


# ── Jinja globals & filters ────────────────────────────────────────────────────

def risk_class(score) -> str:
    """Return a CSS class string based on the 1-10 risk score."""
    score = int(score or 0)
    if score >= 7:
        return "risk-high"
    if score >= 4:
        return "risk-mid"
    return "risk-low"


app.jinja_env.globals["risk_class"] = risk_class


@app.template_filter("thousands")
def thousands_filter(value):
    """Format a number with comma thousands separators, no decimal places."""
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return value


@app.template_filter("fmtdate")
def fmtdate_filter(value):
    """Format an ISO date string as 'Mon D' (e.g. 'Apr 9')."""
    try:
        from datetime import date
        d = date.fromisoformat(str(value))
        return f"{d.strftime('%b')} {d.day}"
    except (ValueError, TypeError):
        return value


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    reports = db.get_reports()
    total_asteroids = db.get_total_asteroid_count()
    next_approach = db.get_next_approach()
    approach_timeline = db.get_approach_timeline()
    return render_template(
        "index.html",
        reports=reports,
        total_asteroids=total_asteroids,
        next_approach=next_approach,
        approach_timeline=approach_timeline,
    )


@app.route("/report/<int:report_id>")
def report_detail(report_id: int):
    report, asteroids = db.get_report(report_id)
    if report is None:
        abort(404)
    return render_template("report.html", report=report, asteroids=asteroids)


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
