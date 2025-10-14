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
def fetch_reports(report_type="daily_reports"):
    res = supabase.table(report_type).select("*").order("date", desc=False).execute()
    return res.data

st.title("🧭 Mall of Tripla — Visitor Experience & Retail Performance Brief")

# Select report type
report_type = st.selectbox("Report Type", ["daily_reports", "weekly_reports", "monthly_reports"])
reports = fetch_reports(report_type)

# Select a report
report_dates = [r["date"] for r in reports]
selected_date = st.selectbox("Select Reporting Period", report_dates)

# Load the JSON report from Supabase
selected_report = next(r for r in reports if r["date"] == selected_date)
report_json = json.loads(selected_report["report_text"])  # assuming report_text stores JSON

# Overview
st.subheader("Overview")
overview = report_json.get("overview", {})
st.markdown(f"- Total Questions: {overview.get('total_question_count', '-')}")
st.markdown(f"- Average Match Score: {overview.get('average_match_score', '-')}")
st.markdown(f"- Complete Misses: {overview.get('complete_misses', '-')}")
st.markdown(f"- Complete Misses Rate: {overview.get('complete_misses_rate', '-')}")
st.markdown(f"- Sentiment: {overview.get('sentiment', '-')}")
st.markdown(f"- Peak Interaction Times: {overview.get('peak_interaction_times', '-')}")

# Topics
st.subheader("Topics & Themes")
for idx, topic in enumerate(report_json.get("topics", []), 1):
    st.markdown(f"### {idx}️⃣ Theme: {topic['topic']}")
    st.markdown(f"**Observation:** {topic.get('observation', '')}")
    st.markdown(f"**Implication:** {topic.get('implication', '')}")
    st.markdown(f"**Strategic Alignment:** {topic.get('strategic_alignment', '')}")
    st.markdown(f"**Recommendation:** {topic.get('recommendation', '')}")
    st.markdown(f"**Decision Required:** {topic.get('decision_required', '')}")
    st.markdown("---")

# Recommended actions / executive summary
st.subheader("🔚 Executive Summary — At a Glance")
for action in report_json.get("recommended_actions", []):
    st.markdown(f"- **{action['priority'].capitalize()}**: {action['recommendation']} — Impact: {action['impact']}")

# Overall Takeaway
st.subheader("🧩 Overall Takeaway")
st.markdown(report_json.get("overall_takeaway", "-"))