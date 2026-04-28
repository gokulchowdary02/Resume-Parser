import streamlit as st
import pdfplumber
import docx
import re
import spacy
import pandas as pd

from skills import SKILLS
from job_roles import JOB_ROLES

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

nlp = spacy.load("en_core_web_sm")

st.set_page_config(page_title="AI Resume Analyzer", layout="wide")

# -------------------------------
# 🎨 UI (UNCHANGED)
# -------------------------------
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

# -------------------------------
# SESSION STATE (NEW FIX)
# -------------------------------
if "results" not in st.session_state:
    st.session_state.results = []

if "pdf" not in st.session_state:
    st.session_state.pdf = None

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.header("📂 Upload & Configure")

uploaded_files = st.sidebar.file_uploader(
    "Upload Resumes",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

job_desc = st.sidebar.text_area("Job Description")

ACCEPT_THRESHOLD = st.sidebar.slider("Hiring Threshold (%)", 0, 100, 50)

analyze_btn = st.sidebar.button("🚀 Analyze Candidates")

# -------------------------------
# FUNCTIONS
# -------------------------------
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

    content = []
    content.append(Paragraph("<b>AI Resume Analysis Report</b>", styles["Title"]))
    content.append(Spacer(1, 20))

    if results:
        best = max(results, key=lambda x: x["jd_score"])
        content.append(Paragraph(
            f"<b>Best Candidate:</b> {best['file']} ({best['jd_score']}%)",
            styles["Normal"]
        ))
        content.append(Spacer(1, 10))

        for c in results:
            text = f"""
            <b>{c['file']}</b><br/>
            Score: {c['jd_score']}%<br/>
            Decision: {c['decision']}<br/>
            Skills: {', '.join(c['skills'])}<br/><br/>
            """
            content.append(Paragraph(text, styles["Normal"]))

    doc.build(content)
    return file_path


# -------------------------------
# PROCESS (UPDATED TO SESSION)
# -------------------------------
if analyze_btn and uploaded_files:
    st.session_state.results = []

    for file in uploaded_files:
        text = extract_text(file)

        tokens = preprocess_text(text)
        skills = extract_skills(text, tokens)

        jd_score, matched = match_with_jd(skills, job_desc)

        decision = "Hire" if jd_score >= ACCEPT_THRESHOLD else "Reject"

        st.session_state.results.append({
            "file": file.name,
            "skills": skills,
            "jd_score": jd_score,
            "matched_skills": matched,
            "text": text,
            "decision": decision
        })

# -------------------------------
# OUTPUT
# -------------------------------
results = st.session_state.results

if results:

    best = max(results, key=lambda x: x["jd_score"])
    avg = sum([c["jd_score"] for c in results]) / len(results)

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Best Match", f"{best['jd_score']}%")
    col2.metric("Average Score", f"{round(avg,1)}%")
    col3.metric("Candidates", len(results))
    st.markdown("---")

    # Best Candidate
    st.markdown("### 🏆 Best Candidate")
    st.markdown(f"""
    <div class="card">
    <b>{best['file']}</b><br>
    Match Score: <span class="badge">{best['jd_score']}%</span><br>
    Decision: <b>{best['decision']}</b><br>
    Matched Skills: {', '.join(best['matched_skills'])}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Table
    st.markdown("### 📊 Candidate Comparison")
    df = pd.DataFrame(results)
    st.dataframe(df[["file", "jd_score", "decision"]])

    st.markdown("---")

    # Candidates
    st.markdown("### 📂 Candidates")

    for c in sorted(results, key=lambda x: x["jd_score"], reverse=True):

        color = "#22c55e" if c["decision"] == "Hire" else "#ef4444"

        st.markdown(f"""
        <div class="card">
        <b>{c['file']}</b><br>
        Match Score: <span class="badge">{c['jd_score']}%</span><br>
        Decision: <span style="color:{color}; font-weight:bold;">{c['decision']}</span><br>
        Matched Skills: {', '.join(c['matched_skills'])}
        </div>
        """, unsafe_allow_html=True)

        st.progress(c["jd_score"] / 100)

        with st.expander("📄 View Resume"):
            st.markdown(f"""
            <div style="background:#0f172a; padding:15px; border-radius:10px;">
            {c["text"][:2000].replace('\n','<br>')}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

    # Hiring Recommendation
    st.markdown("### 🧑‍💼 Hiring Recommendation")

    for c in results:
        if c["decision"] == "Hire":
            st.success(f"Hire: {c['file']}")
        else:
            st.error(f"Reject: {c['file']}")

    st.markdown("---")

    # -------------------------------
    # 📄 REPORT (FIXED)
    # -------------------------------
    st.markdown("### 📄 Report")

    if st.button("Generate PDF Report"):
        path = generate_pdf(results)
        with open(path, "rb") as f:
            st.session_state.pdf = f.read()

    if st.session_state.pdf:
        st.download_button(
            "📥 Download PDF",
            data=st.session_state.pdf,
            file_name="report.pdf",
            mime="application/pdf"
        )
    st.markdown("---")


    # Chart
    st.markdown("### 📈 Score Comparison")

    chart_df = pd.DataFrame({
        "Candidate": [c["file"] for c in results],
        "Score": [c["jd_score"] for c in results]
    })

    st.bar_chart(chart_df.set_index("Candidate"))