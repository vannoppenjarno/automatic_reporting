from dotenv import load_dotenv  
from supabase import create_client
import streamlit as st
import json
import os

# To run the app: python -m streamlit run visualize.py

load_dotenv()  

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@st.cache_data
def fetch_reports(report_type="Daily"):
    res = supabase.table(report_type).select("*").order("date", desc=False).execute()
    return res.data

st.title("🧭 Mall of Tripla — Visitor Experience & Retail Performance Brief")

# Select report type
report_type = st.selectbox("Report Type", ["Daily", "Weekly", "Monthly"])
reports = fetch_reports(report_type)

# Select a report
report_dates = [r["date"] for r in reports]
selected_date = st.selectbox("Select Reporting Period", report_dates)

# Load the JSON report from Supabase
selected_report = next(r for r in reports if r["date"] == selected_date)
report_json = json.loads(selected_report["report_text"])  # assuming report_text stores JSON

# Title
st.header(report_json.get("title", "Mall of Tripla Report"))

# Visitor Interactions
st.metric(label="📊 Total Visitor Interactions", value=json.loads(selected_report["n_logs"]))

# Topics
st.subheader("Topics & Themes")
for idx, topic in enumerate(report_json.get("topics", []), 1):
    st.markdown(f"#### {idx}️⃣ Theme: {topic['topic']}")
    st.markdown(f"**Observation:** {topic.get('observation', '-')}")
    st.markdown(f"**Implication:** {topic.get('implication', '-')}")
    strategic = topic.get("strategic_alignment", {})
    st.markdown(f"**Strategic Alignment:** {strategic.get('objective', '-')} → Status: {strategic.get('status', '-')}")

    recommendation = topic.get("recommendation", {})
    st.markdown(f"**Recommendation (Priority: {recommendation.get('priority', '-')})**: {recommendation.get('action', '-')}")
    if recommendation.get("alternative"):
        st.markdown(f"**Alternative:** {recommendation.get('alternative', '-')}")
    st.markdown(f"**Expected Impact:** {recommendation.get('impact', '-')}")

    st.markdown(f"**Decision Required:** {topic.get('decision_required', '-')}")
    st.divider()

# Executive Summary
st.subheader("🔚 Executive Summary — At a Glance")
for summary in report_json.get("executive_summary", []):
    st.markdown(f"- **Objective:** {summary.get('objective', '-')}")
    st.markdown(f"  - Status: {summary.get('status', '-')}")
    st.markdown(f"  - Key Decision Needed: {summary.get('key_decision_needed', '-')}")
    st.markdown("")

# Overall Takeaway
st.subheader("🧩 Overall Takeaway")
st.markdown(report_json.get("overall_takeaway", "-"))