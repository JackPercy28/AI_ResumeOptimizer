import streamlit as st
from dotenv import load_dotenv
from groq import Groq
import PyPDF2
import extra_streamlit_components as stx
import json
import re
from dashboard import render_dashboard
from jobs import fetch_malaysia_jobs

# ── Setup ──────────────────────────────────────────────────────────────────
load_dotenv()
client = Groq()
cookie_manager = stx.CookieManager()

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OptiResume",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stHeaderActionElements"] { visibility: hidden; }
    header { background-color: transparent !important; }
    footer { visibility: hidden; }
    .stApp, [data-testid="stSidebar"] {
        background-color: #0f0f14 !important;
        color: #e8e8f0 !important;
    }
    .stChatMessage {
        border-radius: 16px;
        background-color: #1a1a24 !important;
        border: 1px solid #2a2a3a !important;
    }
    .stChatInputContainer {
        border-radius: 28px !important;
        background-color: #1a1a24 !important;
        border: 1px solid #2a2a3a !important;
    }
    [data-testid="stChatInputTextArea"] { color: #e8e8f0 !important; }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1a1a24;
        border-radius: 12px;
        padding: 4px;
        gap: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #888;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2a2a3a !important;
        color: #e8e8f0 !important;
    }
    div[data-testid="stIframe"] { border-radius: 16px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────
MAX_MESSAGES = 10
USER_ICON = "👤"
AI_ICON = "✨"

# ── Session state defaults ─────────────────────────────────────────────────
if "message_count" not in st.session_state:
    saved = cookie_manager.get("usage_count")
    st.session_state.message_count = int(saved) if saved else 0

if "message_history" not in st.session_state:
    st.session_state.message_history = [
        {"role": "assistant", "content": (
            "👋 Hi there! I'm your AI Career Coach. "
            "Upload your resume on the left to get a full analytics report, "
            "or tell me what roles you're aiming for so we can get started!"
        )}
    ]

if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ✨ OptiResume")
    st.markdown("*Your elite career coach*")
    st.divider()

    uploaded_file = st.file_uploader("📄 Upload Resume (PDF)", type=["pdf"])

    if uploaded_file:
        if uploaded_file.name != st.session_state.get("uploaded_filename"):
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            st.session_state.resume_text = text
            st.session_state.uploaded_filename = uploaded_file.name
            st.session_state.analysis_data = None  # trigger fresh analysis
            st.success(f"✅ {uploaded_file.name} loaded!")

    st.divider()

    messages_left = MAX_MESSAGES - st.session_state.message_count
    pct = messages_left / MAX_MESSAGES
    color = "#1D9E75" if pct > 0.5 else "#EF9F27" if pct > 0.2 else "#E24B4A"
    st.markdown(f"""
    <div style='font-size:12px;color:#888;margin-bottom:6px;'>Free messages remaining</div>
    <div style='font-size:22px;font-weight:600;color:{color};'>{messages_left} / {MAX_MESSAGES}</div>
    """, unsafe_allow_html=True)
    st.progress(max(pct, 0))

    if st.session_state.analysis_data:
        st.divider()
        d = st.session_state.analysis_data
        kf = len(d.get('keywords_found', []))
        kt = kf + len(d.get('keywords_missing', []))
        st.markdown(f"""
        <div style='font-size:12px;color:#888;'>Quick stats</div>
        <div style='font-size:13px;margin-top:8px;line-height:2.2;'>
            🎯 ATS Score: <b>{d.get('ats_score', '—')}/100</b><br>
            🔑 Keywords: <b>{kf}/{kt}</b><br>
            💼 Job matches: <b>{len(d.get('job_matches', []))}</b>
        </div>
        """, unsafe_allow_html=True)


# ── Analysis system prompt ─────────────────────────────────────────────────
ANALYSIS_SYSTEM_PROMPT = """You are an expert ATS (Applicant Tracking System) analyst and career coach.

Analyze the provided resume and return ONLY a valid JSON object with NO extra text, markdown, or explanation.

The JSON must follow this exact schema:
{
  "ats_score": <integer 0-100>,
  "skills": [
    {"name": "<field name, max 18 chars>", "score": <integer 0-100>, "color": "<hex color>"},
    ... (6-8 skills total)
  ],
  "job_matches": [
    {"title": "<job title>", "company": "<company name>", "location": "<city or Remote>", "match_pct": <integer 0-100>},
    ... (5 jobs total)
  ],
  "keywords_found": ["keyword1", "keyword2", ...],
  "keywords_missing": ["keyword1", "keyword2", ...],
  "bullet_quality": <integer 0-10>,
  "word_count": <integer>,
  "formatting_issues": <integer>,
  "action_verbs_count": <integer>,
  "quantified_bullets": <integer>,
  "total_bullets": <integer>,
  "section_completeness": <integer 0-10>,
  "percentile_note": "<short sentence, e.g. '12% above avg for Software Engineer roles'>",
  "ats_label": "<one of: Needs Work, Fair, Good, Excellent>"
}

Use these hex colors for skills (pick contextually):
- Technical: #378ADD
- Leadership: #D85A30
- Communication: #1D9E75
- Management: #7F77DD
- Data/Analytics: #378ADD
- Problem Solving: #1D9E75
- Soft Skills: #EF9F27
- Domain Knowledge: #D4537E

Return ONLY the JSON. No preamble. No markdown fences."""


def run_analysis(resume_text: str) -> dict | None:
    """Call Groq to analyze the resume and return structured JSON."""
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this resume:\n\n{resume_text}"},
            ],
            temperature=0.3,
            max_tokens=1500,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)
    except Exception as e:
        st.error(f"Analysis error: {e}")
        return None


# ── Chat system prompt ─────────────────────────────────────────────────────
def build_system_prompt() -> str:
    base = """You are an elite Career Coach and Executive Recruiter for top-tier tech and Fortune 500 companies.

CORE METHODOLOGIES:
1. XYZ Format: Push users to rewrite bullets as "Accomplished [X] as measured by [Y], by doing [Z]."
2. Fluff Eradication: Eliminate jargon, buzzwords, and weak verbs ("helped", "assisted", "responsible for").
3. ATS Optimization: Advise on formatting and keyword alignment without keyword stuffing.

YOUR TONE:
- Highly encouraging but brutally honest.
- Always provide a concrete rewritten example when pointing out a flaw.
- Use bullet points and bold text for readability.
- Keep responses concise and actionable."""

    if st.session_state.resume_text:
        base += f"\n\nThe user's resume has been uploaded. Here it is:\n{st.session_state.resume_text}"

    if st.session_state.analysis_data:
        d = st.session_state.analysis_data
        base += (
            f"\n\nAnalysis results: ATS Score={d.get('ats_score')}, "
            f"Missing keywords={d.get('keywords_missing')}, "
            f"Bullet quality={d.get('bullet_quality')}/10"
        )

    return base


# ── Chat UI ────────────────────────────────────────────────────────────────
def _chat_ui():
    for msg in st.session_state.message_history:
        icon = USER_ICON if msg["role"] == "user" else AI_ICON
        with st.chat_message(msg["role"], avatar=icon):
            st.write(msg["content"])

    user_input = st.chat_input("Ask for feedback, interview prep, or to rewrite a bullet point...")

    if user_input:
        if st.session_state.message_count >= MAX_MESSAGES:
            st.error("⚠️ Free trial exhausted. Please clear cookies to reset.")
            st.stop()

        with st.chat_message("user", avatar=USER_ICON):
            st.write(user_input)

        st.session_state.message_history.append({"role": "user", "content": user_input})

        messages_to_send = (
            [{"role": "system", "content": build_system_prompt()}]
            + st.session_state.message_history
        )

        with st.chat_message("assistant", avatar=AI_ICON):
            with st.spinner("Thinking..."):
                completion = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages_to_send,
                    max_tokens=800,
                )
                ai_response = completion.choices[0].message.content
            st.write(ai_response)

        st.session_state.message_history.append({"role": "assistant", "content": ai_response})
        st.session_state.message_count += 1
        cookie_manager.set("usage_count", st.session_state.message_count)
        st.rerun()


# ── Main UI ────────────────────────────────────────────────────────────────
if st.session_state.resume_text:
    tab1, tab2 = st.tabs(["📊  Analytics Dashboard", "💬  Career Coach Chat"])

    with tab1:
        if st.session_state.analysis_data is None:
            with st.spinner("🔍 Analyzing your resume — this takes a few seconds..."):
                data = run_analysis(st.session_state.resume_text)
                if data:
                    # ── Fetch real Malaysian jobs from JSearch ──────────────
                    with st.spinner("🌏 Finding real Malaysian job matches..."):
                        # Pull job title hints from Groq's fake job_matches
                        ai_titles = [
                            j.get("title", "") 
                            for j in data.get("job_matches", [])
                        ][:3]
                        # Fallback: use top keywords as search terms
                        if not ai_titles:
                            ai_titles = [data.get("keywords_found", ["Developer"])[0]]

                        real_jobs = fetch_malaysia_jobs(
                            job_titles=ai_titles,
                            keywords_found=data.get("keywords_found", []),
                            max_results=6,
                        )
                        # Replace AI-hallucinated jobs with real ones
                        data["job_matches"] = real_jobs
                        data["job_count"] = len(real_jobs)

                    st.session_state.analysis_data = data
                    st.rerun()
                else:
                    st.error("Could not analyze resume. Please try again.")
        else:
            html_content = render_dashboard(st.session_state.analysis_data)
            st.components.v1.html(html_content, height=840, scrolling=True)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Re-analyze Resume", use_container_width=True):
                    st.session_state.analysis_data = None
                    st.rerun()
            with col2:
                if st.button("💬 Get coaching tips ↗", use_container_width=True):
                    st.session_state.message_history.append({
                        "role": "user",
                        "content": "Based on my resume analysis, what are the top 3 things I should fix first?"
                    })
                    st.info("Switch to the 'Career Coach Chat' tab for your personalized tips!")

    with tab2:
        _chat_ui()

else:
    # Hero landing when no resume uploaded
    if len(st.session_state.message_history) == 1:
        st.markdown("""
        <div style='text-align:center; margin-top:10vh;'>
            <div style='font-size:3.5rem;'>✨</div>
            <h1 style='font-size:2.8rem;font-weight:700;margin:12px 0 8px;'>OptiResume</h1>
            <p style='color:#888;font-size:1.15rem;'>Your elite career coach & resume analyzer</p>
            <p style='color:#555;font-size:0.95rem;margin-top:24px;'>
                Upload your resume in the sidebar to unlock the full analytics dashboard
            </p>
        </div>
        """, unsafe_allow_html=True)

    _chat_ui()