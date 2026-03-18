import streamlit as st # type: ignore
import os
from database import init_db, execute_query, fetch_one, delete_analysis, delete_all_history, delete_resume # type: ignore
from auth import signup_user, login_user # type: ignore
from resume_parser import parse_resume, extract_text_from_pdf, extract_text_from_docx # type: ignore
from opportunity_scraper import scrape_opportunity, detect_opportunity_type # type: ignore
from analyzer import analyze_with_ai, analyze_fallback # type: ignore

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ResumeAnalyzer",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()

# ── Session state defaults
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# Load Gemini key safely
if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = st.secrets.get("GEMINI_API_KEY", "")

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;900&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif !important;
}
#MainMenu, footer { visibility:hidden; }
header { 
    background-color: transparent !important;
}
/* Hide extra Streamlit header icons but keep sidebar toggle */
header [data-testid="stHeaderActionSet"] button:not([aria-label="Toggle sidebar"]) {
    visibility: hidden;
}

@media (max-width: 768px) {
    .block-container {
        padding: 1rem 1rem !important;
    }
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #1a1a1a !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: #f5f0e6 !important; }
[data-testid="stSidebar"] .stRadio label {
    padding: 10px 14px !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    cursor: pointer;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: #2a2a2a !important;
}

/* Main */
.block-container {
    padding: 2rem 2.5rem !important;
    max-width: 1100px !important;
}

/* Prevent login card from becoming too wide */
.auth-card {
    max-width: 420px;
    margin-left: auto;
    margin-right: auto;
}

/* Better mobile spacing */
@media (max-width: 768px) {
    .block-container {
        padding: 1rem 1rem !important;
    }
}

/* Buttons */
.stButton > button {
    background: #22c55e !important;
    color: #1a1a1a !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 0.6rem 2rem !important;
    font-weight: 800 !important;
    font-size: 0.95rem !important;
    box-shadow: 0 4px 15px rgba(34,197,94,.3) !important;
    transition: transform 0.15s, opacity 0.15s !important;
}
.stButton > button:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
    color: #1a1a1a !important;
}

/* Inputs */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background: #fff !important;
    border: 2px solid #e5e0d5 !important;
    border-radius: 10px !important;
    color: #1a1a1a !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #22c55e !important;
    box-shadow: 0 0 0 3px rgba(34,197,94,.15) !important;
}
.stTextInput label, .stTextArea label,
.stSelectbox label, .stFileUploader label {
    font-weight: 700 !important;
    color: #555 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div {
    background: #fff !important;
    border: 2px solid #e5e0d5 !important;
    border-radius: 10px !important;
    color: #1a1a1a !important;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #fff;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    border: 1px solid #e5e0d5;
    box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
[data-testid="stMetricLabel"] {
    color: #888 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}
[data-testid="stMetricValue"] {
    color: #1a1a1a !important;
    font-size: 2.2rem !important;
    font-weight: 900 !important;
}

/* Progress bar */
[data-testid="stProgress"] > div > div > div > div {
    background: #22c55e !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #ede8dc;
    border-radius: 12px;
    gap: 4px;
    padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    color: #666 !important;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background: #1a1a1a !important;
    color: #f5f0e6 !important;
}

/* Expander */
.streamlit-expander {
    border: 1px solid #e5e0d5 !important;
    border-radius: 12px !important;
    background: #fff !important;
}

/* API key banner */
.api-banner {
    background: #fffbeb;
    border: 1px solid #fcd34d;
    border-radius: 12px;
    padding: 14px 18px;
    margin-bottom: 1.5rem;
    font-size: 0.9rem;
    color: #92400e;
}
</style>
""", unsafe_allow_html=True)

# ── Session State ─────────────────────────────────────────────────────────────
# Auto-load Gemini key from .streamlit/secrets.toml (set by developer, invisible to users)
_backend_key = st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, 'secrets') else ""

for k, v in [('logged_in', False), ('user', None),
              ('gemini_key', _backend_key), ('dark_mode', False)]:
    if k not in st.session_state:
        st.session_state[k] = v

def inject_theme():
    """Inject dark-mode CSS overrides when dark mode is active."""
    if st.session_state.dark_mode:
        st.markdown("""
        <style>
        /* Dark base */
        .stApp, .block-container { background-color: #12141c !important; }

        /* Text */
        .stApp p, .stApp div, .stApp span, .stApp label,
        .stApp h1, .stApp h2, .stApp h3, .stApp li {
            color: #cdd6f4 !important;
        }

        /* Metric cards */
        [data-testid="stMetric"] {
            background: #1e2030 !important;
            border-color: #313244 !important;
        }
        [data-testid="stMetricLabel"] { color: #a6adc8 !important; }
        [data-testid="stMetricValue"] { color: #cdd6f4 !important; }

        /* Custom HTML cards (background:#fff) */
        div[style*="background:#fff"] {
            background: #1e2030 !important;
            border-color: #313244 !important;
        }

        /* Inline text inside cards */
        div[style*="color:#1a1a1a"] { color: #cdd6f4 !important; }
        div[style*="color:#888"]    { color: #6c7086 !important; }

        /* Inputs */
        [data-testid="stTextInput"] input,
        [data-testid="stTextArea"] textarea {
            background: #1e2030 !important;
            color: #cdd6f4 !important;
            border-color: #45475a !important;
        }
        [data-testid="stTextInput"] label,
        [data-testid="stTextArea"] label { color: #a6adc8 !important; }

        /* Selectbox */
        [data-testid="stSelectbox"] > div > div {
            background: #1e2030 !important;
            color: #cdd6f4 !important;
            border-color: #45475a !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] { background: #1e2030 !important; }
        .stTabs [data-baseweb="tab"] { color: #a6adc8 !important; }
        .stTabs [aria-selected="true"] {
            background: #22c55e !important;
            color: #12141c !important;
        }

        /* Expander */
        .streamlit-expander {
            background: #1e2030 !important;
            border-color: #313244 !important;
        }

        /* File uploader */
        [data-testid="stFileUploader"] {
            background: #1e2030 !important;
            border-color: #45475a !important;
        }

        /* Info / success / warning boxes */
        [data-testid="stAlert"] { background: #1e2030 !important; }
        </style>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# UI HELPERS
# ═══════════════════════════════════════════════════════════
def skill_badge(text, matched=True):
    bg   = "#dcfce7" if matched else "#fee2e2"
    col  = "#15803d" if matched else "#dc2626"
    bord = "#86efac" if matched else "#fca5a5"
    return (f"<span style='background:{bg};color:{col};border:1px solid {bord};"
            f"border-radius:50px;padding:4px 14px;font-size:0.82rem;font-weight:700;"
            f"margin:3px;display:inline-block'>{text}</span>")

def section_card(title, body_html, accent="#22c55e"):
    st.markdown(f"""
    <div style="background:#fff;border:1px solid #e5e0d5;border-radius:16px;
                padding:1.6rem;margin-bottom:1.2rem;
                box-shadow:0 2px 8px rgba(0,0,0,.05);">
        <div style="color:{accent};font-size:0.7rem;font-weight:800;
                    text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px;">
            {title}
        </div>
        <div style="color:#1a1a1a;line-height:1.75;font-size:0.95rem;">
            {body_html}
        </div>
    </div>""", unsafe_allow_html=True)

def hero_score(score):
    if score >= 70:
        col = "#22c55e"; label = "Excellent Match 🎉"
    elif score >= 45:
        col = "#f59e0b"; label = "Moderate Match 🔶"
    else:
        col = "#ef4444"; label = "Weak Match ⚠️"

    st.markdown(f"""
    <div style="background:#1a1a1a;border-radius:20px;padding:3rem 2rem;
                text-align:center;margin:1.5rem 0;">
        <div style="font-size:6rem;font-weight:900;color:{col};line-height:1;">{score}%</div>
        <div style="color:{col};font-size:1.1rem;font-weight:700;margin-top:6px;
                    text-transform:uppercase;letter-spacing:2px;">{label}</div>
        <div style="color:#666;font-size:0.85rem;margin-top:6px;">AI Compatibility Score</div>
    </div>""", unsafe_allow_html=True)
    st.progress(score / 100)

def page_title(text, subtitle=""):
    st.markdown(f"<div style='font-size:2.2rem;font-weight:900;color:#1a1a1a;margin-bottom:4px;'>{text}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div style='color:#888;margin-bottom:2rem;font-size:1rem;'>{subtitle}</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# AUTH PAGE
# ═══════════════════════════════════════════════════════════
def login_page():

    c1, c2, c3 = st.columns([0.5, 2, 0.5])
    with c2:

        st.markdown("""
        <style>

        /* AUTH CARD */
        .auth-card {
            padding:2.5rem 2rem;
            border-radius:16px;
            background:#ffffff;
            box-shadow:0 10px 35px rgba(0,0,0,0.08);
            margin-top:3rem;
            margin-bottom:3rem;
        }

        /* TITLE */
        .auth-title{
            font-size:2.8rem;
            font-weight:900;
            letter-spacing:-1px;
            text-align:center;
            margin-bottom:0.4rem;
        }

        /* SUBTITLE */
        .auth-sub{
            text-align:center;
            color:#777;
            margin-bottom:1.8rem;
            font-size:0.95rem;
        }

        /* MOBILE RESPONSIVENESS */
        @media (max-width: 768px){

            .auth-card{
                padding:1.8rem 1.3rem;
                margin-top:1.5rem;
                margin-bottom:1.5rem;
            }

            .auth-title{
                font-size:2rem;
            }

            .auth-sub{
                font-size:0.85rem;
            }

            .stTextInput > div > div > input{
                font-size:0.9rem;
                padding:0.5rem;
            }

            button[kind="secondary"]{
                width:100%;
            }

        }

        </style>
        """, unsafe_allow_html=True)

        # Card start
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)

        st.markdown("""
        <div class="auth-title">✦ ResumeAnalyzer</div>
        <div class="auth-sub">AI-powered resume matching for every opportunity</div>
        """, unsafe_allow_html=True)

        tab_l, tab_s = st.tabs(["🔑 Login", "📝 Sign Up"])

        # LOGIN TAB
        with tab_l:

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            uname = st.text_input(
                "Username",
                key="l_u",
                placeholder="your username"
            )

            pwd = st.text_input(
                "Password",
                type="password",
                key="l_p",
                placeholder="••••••••"
            )

            if st.button("Login →", key="btn_login", use_container_width=True):

                u = login_user(uname, pwd)

                if u:
                    st.session_state.logged_in = True
                    st.session_state.user = dict(u)
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password.")

        # SIGNUP TAB
        with tab_s:

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            nu = st.text_input(
                "Username",
                key="s_u",
                placeholder="choose a username"
            )

            np = st.text_input(
                "Password",
                type="password",
                key="s_p",
                placeholder="choose a password"
            )

            cp = st.text_input(
                "Confirm Password",
                type="password",
                key="s_c",
                placeholder="repeat password"
            )

            if st.button("Create Account →", key="btn_signup", use_container_width=True):

                if np != cp:
                    st.error("❌ Passwords do not match.")

                elif len(nu) < 3:
                    st.error("❌ Username must be at least 3 characters.")

                elif signup_user(nu, np):
                    st.success("✅ Account created! Please login now.")

                else:
                    st.error("❌ Username already exists.")

        st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════
def render_sidebar():
    with st.sidebar:
        st.markdown("""
        <div style="padding:1.8rem 1rem 0.8rem;border-bottom:1px solid #333;margin-bottom:1rem;">
            <div style="font-size:1.1rem;font-weight:900;">✦ ResumeAnalyzer</div>
        </div>""", unsafe_allow_html=True)

        # AI + username status
        has_key = bool(st.session_state.gemini_key)
        ai_dot  = "<span style='color:#22c55e'>●</span> AI Active" if has_key else "<span style='color:#f59e0b'>●</span> Keyword Mode"
        st.markdown(f"<div style='font-size:0.78rem;padding:0 1rem 0.3rem;'>{ai_dot}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='font-size:0.8rem;color:#888;padding:0 1rem 1rem;'>@{st.session_state.user['username']}</div>", unsafe_allow_html=True)

        choice = st.radio("", [
            "🏠  Dashboard",
            "📄  Upload Resume",
            "🔍  Analyze Opportunity",
            "📜  History",
            "👤  Profile",
        ], label_visibility="collapsed")

        st.markdown("<br>", unsafe_allow_html=True)
        st.divider()

        # ── Dark / Light toggle ──────────────────────────────────────────────
        new_dark = st.toggle("🌙 Dark Mode", value=st.session_state.dark_mode,
                             key="sidebar_dark_toggle")
        if new_dark != st.session_state.dark_mode:
            st.session_state.dark_mode = new_dark
            if 'settings_dark_toggle' in st.session_state:
                st.session_state.settings_dark_toggle = new_dark
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Persistent Data Note (SQLite limitation on Streamlit Cloud)
        if "streamlit" in st.secrets.get("DEPLOY_ENV", "").lower():
            st.caption("ℹ️ *Note: On the free tier, history is ephemeral and moves back to baseline periodically.*")
        
        if st.button("🚪  Logout", key="logout_btn"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()

    inject_theme()  # apply dark overrides if toggled
    return choice.split("  ", 1)[1].strip()


# ═══════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════
def page_dashboard():
    uid   = st.session_state.user['id']
    uname = st.session_state.user['username']

    st.markdown(f"""
    <div style="margin-bottom:2rem;">
        <div style="font-size:2.4rem;font-weight:900;color:#1a1a1a;line-height:1.1;">
            Welcome back, <span style="color:#22c55e">{uname}</span> 👋
        </div>
        <div style="color:#888;margin-top:6px;">Here's a snapshot of your activity.</div>
    </div>""", unsafe_allow_html=True)


    rcount = execute_query("SELECT COUNT(*) c FROM resumes WHERE user_id=?", (uid,))[0]['c']
    acount = execute_query("SELECT COUNT(*) c FROM analysis_results WHERE user_id=?", (uid,))[0]['c']
    avg_q  = execute_query("SELECT AVG(score) s FROM analysis_results WHERE user_id=?", (uid,))[0]['s']
    avg_sc = int(avg_q) if avg_q else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("📄 Resumes", rcount)
    c2.metric("🔍 Analyses Run", acount)
    c3.metric("⭐ Avg. Score", f"{avg_sc}%")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:1.4rem;font-weight:800;margin-bottom:1rem;color:#1a1a1a;'>Recent Analyses</div>", unsafe_allow_html=True)

    recent = execute_query("""
        SELECT ar.score, ar.analysis_date, o.title, o.type, r.filename
        FROM analysis_results ar
        JOIN opportunities o ON ar.opportunity_id = o.id
        JOIN resumes r ON ar.resume_id = r.id
        WHERE ar.user_id = ? ORDER BY ar.analysis_date DESC LIMIT 5
    """, (uid,))

    if not recent:
        st.info("No analyses yet — upload a resume and run your first analysis!")
    else:
        for row in recent:
            r = dict(row)
            sc  = r['score']
            col = "#22c55e" if sc >= 70 else "#f59e0b" if sc >= 45 else "#ef4444"
            st.markdown(f"""
            <div style="background:#fff;border:1px solid #e5e0d5;border-radius:14px;
                        padding:1rem 1.4rem;display:flex;align-items:center;
                        justify-content:space-between;margin-bottom:0.6rem;
                        box-shadow:0 2px 6px rgba(0,0,0,.05);">
                <div>
                    <div style="font-weight:700;color:#1a1a1a;">{r['title'] or 'Untitled'}</div> # type: ignore
                    <div style="color:#888;font-size:0.8rem;">{r['filename']} · {r['type']} · {str(r.get('analysis_date', ''))[:10]}</div> # type: ignore
                </div>
                <div style="font-size:2rem;font-weight:900;color:{col}">{sc}%</div> # type: ignore
            </div>""", unsafe_allow_html=True)




# ═══════════════════════════════════════════════════════════
# UPLOAD RESUME
# ═══════════════════════════════════════════════════════════
def page_upload():
    page_title("📄 Upload Resume", "Upload your PDF or DOCX resume. We'll extract and analyse it.")

    uploaded = st.file_uploader("Choose file (PDF or DOCX)", type=["pdf", "docx"])

    if uploaded:
        st.success(f"✅ File selected: **{uploaded.name}**")
        if st.button("⚡ Process & Save"):
            with st.spinner("Reading resume…"):
                try:
                    if uploaded.name.lower().endswith(".pdf"):
                        raw_text = extract_text_from_pdf(uploaded)
                    else:
                        raw_text = extract_text_from_docx(uploaded)

                    if not raw_text or len(raw_text.strip()) < 30:
                        st.error("⚠️ Could not extract text. The PDF may be a scanned image. Try a text-based PDF.")
                        return

                    sections = parse_resume(raw_text)
                    execute_query(
                        "INSERT INTO resumes (user_id, filename, content, skills, education, projects, experience, certifications) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (st.session_state.user['id'], uploaded.name, raw_text,
                         sections['skills'], sections['education'], sections['projects'],
                         sections['experience'], sections['certifications']),
                        commit=True
                    )
                    wc = len(raw_text.split())
                    st.success(f"✅ Resume saved! ({wc} words extracted)")

                    for sec, content in sections.items():
                        if content.strip():
                            section_card(f"📌 {sec.capitalize()}",
                                content.replace('\n', '<br>').strip()[:600] +
                                ("…" if len(content) > 600 else ""))

                except Exception as e:
                    st.error(f"❌ Error: {e}")


# ═══════════════════════════════════════════════════════════
# ANALYZE OPPORTUNITY
# ═══════════════════════════════════════════════════════════
def page_analyze():
    page_title("🔍 Analyze Opportunity",
               "Compare your resume against any job, internship, hackathon, or committee application.")

    uid     = st.session_state.user['id']
    resumes = execute_query("SELECT id, filename FROM resumes WHERE user_id=?", (uid,))
    if not resumes:
        st.warning("⚠️ Please upload a resume first.")
        return

    # API key status nudge
    if not st.session_state.gemini_key:
        st.markdown("""<div class="api-banner">
             Running in <b>Keyword Mode</b>. Add your free Gemini API key in <b>⚙️ Settings</b> for AI-powered analysis.
        </div>""", unsafe_allow_html=True)

    resume_map = {r['filename']: r['id'] for r in resumes}
    sel_name   = st.selectbox("Select Resume", list(resume_map.keys()))
    resume_id  = resume_map[sel_name]

    st.markdown("<br>", unsafe_allow_html=True)
    method = st.radio("Input Method", ["✏️ Paste Description", "🔗 Paste a Link"], horizontal=True)

    opp_title = ""
    opp_text  = ""

    if "Paste Description" in method:
        opp_title = st.text_input("Opportunity Title", placeholder="e.g. Software Engineer Intern — Google")
        opp_text  = st.text_area("Paste the full description here", height=240,
                                  placeholder="Copy the entire job / internship / hackathon description…")
    else:
        link = st.text_input("Opportunity URL", placeholder="https://...")
        if link:
            with st.spinner("Fetching page…"):
                fetched = scrape_opportunity(link)
            if fetched:
                opp_text  = fetched
                opp_title = "Online Opportunity"
                st.success("✅ Page fetched!")
            else:
                st.error("❌ Could not fetch the page. Paste the description manually.")

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🚀 Run AI Analysis" if st.session_state.gemini_key else "🔍 Run Analysis"):
        if not opp_text.strip():
            st.warning("Please enter an opportunity description first.")
            return

        with st.spinner("AI is analyzing your resume…" if st.session_state.gemini_key else "Analyzing…"):
            opp_type = detect_opportunity_type(opp_text)
            opp_id   = execute_query(
                "INSERT INTO opportunities (user_id, title, description, type) VALUES (?, ?, ?, ?)",
                (uid, opp_title or "Untitled", opp_text, opp_type), commit=True
            )

            resume_row = fetch_one("SELECT * FROM resumes WHERE id=?", (resume_id,))
            sections = {
                "content":        resume_row['content']        or "",
                "skills":         resume_row['skills']         or "",
                "education":      resume_row['education']      or "",
                "projects":       resume_row['projects']       or "",
                "experience":     resume_row['experience']     or "",
                "certifications": resume_row['certifications'] or "",
            }

            # Choose AI or fallback
            if st.session_state.gemini_key:
                full_resume = " ".join(v for v in sections.values() if v)
                result = analyze_with_ai(full_resume, opp_text, opp_type, st.session_state.gemini_key)
            else:
                result = analyze_fallback(sections, opp_text, opp_type)

            if result.get('error'):
                st.error(f"❌ AI Error: {result['error']}")
                return

            execute_query(
                "INSERT INTO analysis_results (user_id, resume_id, opportunity_id, score, matched_skills, missing_skills, suggestions) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (uid, resume_id, opp_id, result['score'],
                 result['matched_skills'], result['missing_skills'],
                 "\n".join(result.get('suggestions', []))),
                commit=True
            )

        # ── Display Results ──────────────────────────────────────────────


        st.markdown(f"""
        <div style="margin-top:2rem;margin-bottom:0.5rem;">
            <div style="font-size:1.6rem;font-weight:900;color:#1a1a1a;">
                Results — <span style="color:#22c55e">{opp_type}</span>
            </div>
        </div>""", unsafe_allow_html=True)

        hero_score(result['score'])

        # Summary (AI only)
        if result.get('summary'):
            section_card("📋 AI Summary", result['summary'])

        # Matched & Missing Skills
        col1, col2 = st.columns(2)
        with col1:
            matched = result['matched_skills']
            if matched:
                badges = " ".join(skill_badge(s.strip(), True) for s in matched.split(",") if s.strip())
                section_card("✅ Matched Skills", badges, "#22c55e")
            else:
                section_card("✅ Matched Skills",
                    "<span style='color:#888'>No matching skills found.</span>", "#22c55e")

        with col2:
            missing = result['missing_skills']
            if missing:
                badges = " ".join(skill_badge(s.strip(), False) for s in missing.split(",") if s.strip())
                section_card("❌ Missing Skills", badges, "#ef4444")
            else:
                section_card("❌ Missing Skills",
                    "<span style='color:#888'>No obvious skill gaps!</span>", "#ef4444")

        # Strengths (AI only)
        strengths = result.get('strengths', [])
        if strengths:
            bullets = "".join(f"<div style='margin-bottom:6px;'>✅ {s}</div>" for s in strengths)
            section_card("💪 Your Strengths", bullets, "#6366f1")

        # Suggestions
        suggestions = result.get('suggestions', [])
        if suggestions:
            bullets = "".join(f"<div style='margin-bottom:8px;'>→ {s}</div>" for s in suggestions)
            section_card("💡 Improvement Suggestions", bullets, "#f59e0b")


# ═══════════════════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════════════════
def page_history():
    page_title("📜 History")
    uid  = st.session_state.user['id']

    # ── Confirm-delete state ─────────────────────────────────────────────────
    if 'confirm_clear_all' not in st.session_state:
        st.session_state.confirm_clear_all = False

    hist = execute_query("""
        SELECT ar.*, o.title, o.type, r.filename
        FROM analysis_results ar
        JOIN opportunities o ON ar.opportunity_id = o.id
        JOIN resumes r ON ar.resume_id = r.id
        WHERE ar.user_id = ? ORDER BY ar.analysis_date DESC
    """, (uid,))

    if not hist:
        st.info("No history yet. Run your first analysis!")
        return

    # ── Clear All button ─────────────────────────────────────────────────────
    col_h, col_btn = st.columns([4, 1])
    with col_btn:
        if not st.session_state.confirm_clear_all:
            if st.button("🗑️ Clear All", key="clear_all_btn"):
                st.session_state.confirm_clear_all = True
                st.rerun()
                
    if st.session_state.confirm_clear_all:
        st.warning("⚠️ Are you sure you want to delete ALL history? This cannot be undone.")
        ca, cb, _ = st.columns([1, 1, 3])
        with ca:
            if st.button("Yes, delete all", key="confirm_yes"):
                delete_all_history(uid)
                st.session_state.confirm_clear_all = False
                st.success("✅ All history cleared.")
                st.rerun()
        with cb:
            if st.button("Cancel", key="confirm_no"):
                st.session_state.confirm_clear_all = False
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Individual history entries ───────────────────────────────────────────
    for row in hist:
        h = dict(row)
        sc  = h['score'] # type: ignore
        col = "#22c55e" if sc >= 70 else "#f59e0b" if sc >= 45 else "#ef4444"
        title_label = f"{h['title'] or 'Untitled'}  ·  {sc}%  ·  {str(h['analysis_date'])[:10]}" # type: ignore
        with st.expander(f"  {title_label}"):
            hero_score(sc)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Resume:** {h['filename']}") # type: ignore
                st.markdown(f"**Type:** {h['type']}") # type: ignore
            with c2:
                matched = h['matched_skills'] or "—" # type: ignore
                missing = h['missing_skills'] or "—"
                st.markdown(f"**Matched:** {matched}")
                st.markdown(f"**Missing:** {missing}")
            if h['suggestions']:
                st.info(h['suggestions'])

            st.markdown("<br>", unsafe_allow_html=True)
            # Delete this entry button
            del_key = f"del_hist_{h['id']}"
            if st.button(f"🗑️ Delete this entry", key=del_key):
                delete_analysis(h['id'], uid)
                st.success("Entry deleted.")
                st.rerun()


# ═══════════════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════════════
def page_profile():
    page_title("👤 Profile")
    uid = st.session_state.user['id']

    # ── Account details — native Streamlit (no raw HTML) ─────────────────────
    with st.container():
        st.markdown("**Account Details**")
        col_a, col_b = st.columns(2)
        col_a.metric("Username", st.session_state.user['username']) # type: ignore
        col_b.metric("Member Since", str(st.session_state.user['created_at'])[:10]) # type: ignore

    st.markdown("<br>", unsafe_allow_html=True)

    resumes = execute_query("SELECT id, filename, uploaded_at FROM resumes WHERE user_id=?", (uid,))
    if resumes:
        st.markdown("**Uploaded Resumes**")
        for row in resumes:
            r = dict(row)
            rc1, rc2 = st.columns([5, 1])
            with rc1:
                st.markdown(f"""
                <div style="background:#fff;border:1px solid #e5e0d5;border-radius:12px;
                            padding:0.85rem 1.2rem;margin-bottom:0.5rem;
                            box-shadow:0 2px 6px rgba(0,0,0,.04);">
                    📄 <b>{r['filename']}</b> # type: ignore
                    <span style='color:#888;font-size:0.8rem;float:right;'>
                        {str(r['uploaded_at'])[:10]} # type: ignore
                    </span>
                </div>""", unsafe_allow_html=True)
            with rc2:
                st.markdown("<div style='padding-top:8px'></div>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"del_resume_{r['id']}", # type: ignore
                             help=f"Delete {r['filename']} and all its analyses"):
                    delete_resume(r['id'], uid)
                    st.success(f"'{r['filename']}' deleted.")
                    st.rerun()
    else:
        st.info("No resumes uploaded yet.")


# ═══════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════
if not st.session_state.logged_in:
    login_page()
else:
    page = render_sidebar()
    {
        "Dashboard":           page_dashboard,
        "Upload Resume":       page_upload,
        "Analyze Opportunity": page_analyze,
        "History":             page_history,
        "Profile":             page_profile,
    }.get(page, page_dashboard)()
