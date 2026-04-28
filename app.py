import os
import subprocess
import sys
import time

# --- STEP 1: AUTO-DOWNLOAD SPACY MODEL (DO NOT REMOVE) ---
try:
    import en_core_web_sm
except ImportError:
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
    time.sleep(2)
    import en_core_web_sm

# --- STEP 2: IMPORTS ---
import streamlit as st
import pdfplumber
import docx
import re
import spacy
import pandas as pd

# These must exist in your GitHub repo as skills.py and job_roles.py
from skills import SKILLS
from job_roles import JOB_ROLES

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# --- STEP 3: INITIALIZATION ---
nlp = spacy.load("en_core_web_sm")

st.set_page_config(page_title="AI Resume Analyzer", layout="wide")

# Custom CSS for UI
st.markdown("""<style>
.stApp { background-color: #0f172a; color: #e5e7eb; }
.card { background: #1e293b; padding: 16px; border-radius: 12px; margin-bottom: 12px; }
.badge { padding: 4px 10px; border-radius: 8px; background: linear-gradient(90deg, #6366f1, #8b5cf6); color: white; font-weight: bold; }
.stButton>button { background: linear-gradient(90deg, #6366f1, #8b5cf6); color: white; }
[data-testid="stDownloadButton"] button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    color: white;
    border-radius: 8px;
    font-weight: bold;
}
.stProgress > div > div { background: linear-gradient(90deg, #6366f1, #8b5cf6); }
[data-testid="stMetric"] { background: #1e293b; padding: 15px; border-radius: 12px; text-align: center; }
[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
[data-testid="stMetricValue"] { color: #ffffff !important; font-weight: bold; }
</style>""", unsafe_allow_html=True)

st.title("🚀 RESUME PARSER USING ML")
st.markdown("---")

# Session State for persistency
if "results" not in st.session_state:
    st.session_state.results = []
if "pdf" not in st.session_state:
    st.session_state.pdf = None

# --- SIDEBAR ---
st.sidebar.header("📂 Upload & Configure")
uploaded_files = st.sidebar.file_uploader("Upload Resumes", type=["pdf", "docx"], accept_multiple_files=True)
job_desc = st.sidebar.text_area("Job Description")
ACCEPT_THRESHOLD = st.sidebar.slider("Hiring Threshold (%)", 0, 100, 50)
analyze_btn = st.sidebar.button("🚀 Analyze Candidates")

# --- FUNCTIONS ---
def extract_text(file):
    if file.name.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            return "".join([p.extract_text() or "" for p in pdf.pages])
    elif file.name.endswith(".docx"):
        doc = docx.Document(file)
        return "\n".join([p.text for p in doc.paragraphs])
    return ""

def preprocess_text(text):
    doc = nlp(text)
    return [t.lemma_.lower() for t in doc if not t.is_stop and not t.is_punct]

def extract_skills(text, tokens):
    text_lower = text.lower()
    found = set()
    for skill in SKILLS:
        if skill in text_lower:
            found.add(skill)
    for token in tokens:
        if token in SKILLS:
            found.add(token)
    return list(found)

def match_with_jd(skills, jd):
    jd = jd.lower()
    matched = [s for s in skills if s in jd]
    score = (len(matched) / len(skills)) * 100 if skills else 0
    return round(score, 2), matched

def generate_pdf(results):
    file_path = "resume_report.pdf"
    doc = SimpleDocTemplate(file_path)
    styles = getSampleStyleSheet()
    content = [Paragraph("<b>AI Resume Analysis Report</b>", styles["Title"]), Spacer(1, 20)]
    
    if results:
        best = max(results, key=lambda x: x["jd_score"])
        content.append(Paragraph(f"<b>Best Candidate:</b> {best['file']} ({best['jd_score']}%)", styles["Normal"]))
        content.append(Spacer(1, 10))
