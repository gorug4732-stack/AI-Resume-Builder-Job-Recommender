import csv
import html
import io
import os
import re
 
import streamlit as st
 
st.set_page_config(page_title="AI Resume & Job Finder", page_icon="📄", layout="wide")
 
# Support Streamlit Cloud secrets as well as a local .env file
try:
    if "OPENAI_API_KEY" in st.secrets and not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass
 
# main.py loads .env and creates the OpenAI client on import
BACKEND_ERROR = None
try:
    from main import build_resume_pdf, find_jobs_online
except KeyError:
    BACKEND_ERROR = "OPENAI_API_KEY not found. Add it to your .env file (or Streamlit secrets)."
except Exception as e:  # noqa: BLE001
    BACKEND_ERROR = f"Could not load backend: {e}"
 
# ---------------- Styling ---------------- #
 
st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; max-width: 1100px;}
    .hero {padding: 1.4rem 1.6rem; border-radius: 14px;
           background: linear-gradient(120deg, #1a4d8f 0%, #2f80ed 100%); color: white;}
    .hero h1 {margin: 0; font-size: 1.9rem; color: white;}
    .hero p {margin: .3rem 0 0; opacity: .92;}
    </style>
    <div class="hero">
      <h1>📄 AI Resume Builder & Job Finder</h1>
      <p>Fill in your details, download a professional PDF resume, and get live job matches powered by AI web search.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")
 
# ---------------- Helpers ---------------- #
 
QUALIFICATIONS = ["10th", "12th", "Diploma", "Bachelor's", "Master's", "PhD", "Other"]
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")
 
 
def split_list(text):
    return [x.strip() for x in re.split(r"[,\n]", text) if x.strip()]
 
 
def escape_for_pdf(value):
    """ReportLab Paragraph parses XML-like text, so escape &, <, >."""
    if isinstance(value, str):
        return html.escape(value.strip(), quote=False)
    if isinstance(value, list):
        return [escape_for_pdf(v) for v in value]
    return value
 
 
def validate(f):
    errors = []
    if not f["name"].strip():
        errors.append("Full name is required.")
    if not EMAIL_RE.match(f["email"].strip()):
        errors.append("Enter a valid email address.")
    if not re.fullmatch(r"\d{10}", f["phone"].strip()):
        errors.append("Phone number must be exactly 10 digits.")
    if not f["degree"].strip():
        errors.append("Degree / course is required.")
    if not f["college"].strip():
        errors.append("College / university is required.")
    if not f["preferred_job_role"].strip():
        errors.append("Preferred job role is required.")
    if not split_list(f["technical_skills"]):
        errors.append("Add at least one technical skill.")
    return errors
 
 
def jobs_to_csv(jobs):
    buf = io.StringIO()
    cols = ["title", "company", "location", "salary", "experience",
            "match_percent", "source_site", "apply_url", "reason"]
    writer = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(jobs)
    return buf.getvalue().encode("utf-8")
 
 
def reset_all():
    for key in ("profile", "pdf_bytes", "jobs"):
        st.session_state.pop(key, None)
 
 
# ---------------- Sidebar ---------------- #
 
with st.sidebar:
    st.header("⚙️ Settings")
    job_limit = st.slider("Number of jobs to fetch", 3, 10, 5)
    if BACKEND_ERROR:
        st.error("API key / backend not ready")
    else:
        st.success("Backend connected")
    st.divider()
    st.caption(
        "**How it works**\n\n"
        "1. Enter your details\n"
        "2. Generate your PDF resume\n"
        "3. Search live job openings with match scores"
    )
    st.button("🔄 Start over", on_click=reset_all, use_container_width=True)
 
if BACKEND_ERROR:
    st.error(BACKEND_ERROR)
    st.stop()
 
# ---------------- Tabs ---------------- #
 
tab_form, tab_resume, tab_jobs = st.tabs(["1️⃣ Your Details", "2️⃣ Resume", "3️⃣ Job Matches"])
 
# ----- Tab 1: details form ----- #
with tab_form:
    with st.form("details_form"):
        st.subheader("Personal information")
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Full name *", placeholder="Jatinder Kumar")
        email = c2.text_input("Email *", placeholder="you@example.com")
        phone = c3.text_input("Phone (10 digits) *", placeholder="9876543210", max_chars=10)
 
        st.subheader("Education")
        c1, c2 = st.columns(2)
        qualification = c1.selectbox("Highest qualification", QUALIFICATIONS, index=3)
        degree = c2.text_input("Degree / course *", placeholder="B.Tech Computer Science")
        c1, c2 = st.columns([3, 1])
        college = c1.text_input("College / university *")
        passout_year = c2.number_input("Passout year", 1990, 2035, 2025, step=1)
 
        st.subheader("Experience")
        c1, c2 = st.columns([1, 3])
        experience_years = c1.number_input("Years of experience", 0.0, 40.0, 0.0, step=0.5)
        job_title = c2.text_input("Current / previous job title", placeholder="Python Developer Intern")
 
        st.subheader("Skills & achievements")
        technical_skills = st.text_area(
            "Technical skills * (comma separated)",
            placeholder="Python, FastAPI, scikit-learn, LangChain, SQL",
        )
        projects = st.text_area(
            "Projects (comma or new line separated)",
            placeholder="AI Resume Builder, Car Price Prediction API",
        )
        certifications = st.text_area("Certifications (comma or new line separated)")
 
        st.subheader("Job preferences")
        c1, c2, c3 = st.columns(3)
        preferred_job_role = c1.text_input("Preferred job role *", placeholder="AI Engineer")
        preferred_locations = c2.text_input("Preferred locations", placeholder="Remote, Chandigarh, Bengaluru")
        expected_salary = c3.text_input("Expected salary", placeholder="6 LPA")
 
        submitted = st.form_submit_button("✨ Generate Resume", type="primary", use_container_width=True)
 
    if submitted:
        form = {
            "name": name, "email": email, "phone": phone, "degree": degree,
            "college": college, "preferred_job_role": preferred_job_role,
            "technical_skills": technical_skills,
        }
        errors = validate(form)
        if errors:
            for err in errors:
                st.error(err)
        else:
            exp_text = (f"{experience_years:g} years" if experience_years else "Fresher")
            profile = {
                "name": name.strip(), "email": email.strip(), "phone": phone.strip(),
                "qualification": qualification, "degree": degree.strip(),
                "college": college.strip(), "passout_year": str(int(passout_year)),
                "experience": exp_text, "job_title": job_title.strip(),
                "technical_skills": split_list(technical_skills),
                "projects": split_list(projects),
                "certifications": split_list(certifications),
                "preferred_job_role": preferred_job_role.strip(),
                "preferred_locations": split_list(preferred_locations),
                "expected_salary": expected_salary.strip(),
            }
            try:
                with st.spinner("Building your resume..."):
                    pdf_bytes = build_resume_pdf(escape_for_pdf(profile))
                st.session_state.profile = profile
                st.session_state.pdf_bytes = pdf_bytes
                st.session_state.pop("jobs", None)
                st.success("Resume ready! Open the **Resume** tab to download it.")
            except Exception as e:  # noqa: BLE001
                st.error(f"Could not generate the resume: {e}")
 
# ----- Tab 2: resume ----- #
with tab_resume:
    if "pdf_bytes" not in st.session_state:
        st.info("Fill in your details in the first tab and click **Generate Resume**.")
    else:
        p = st.session_state.profile
        st.subheader(f"Resume for {p['name']}")
        st.download_button(
            "⬇️ Download PDF Resume",
            data=st.session_state.pdf_bytes,
            file_name=f"{p['name'].replace(' ', '_')}_Resume.pdf",
            mime="application/pdf",
            type="primary",
        )
        st.write("")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Contact**")
            st.write(f"📧 {p['email']}  \n📞 {p['phone']}")
            st.markdown("**Education**")
            st.write(f"{p['degree']} — {p['college']} ({p['passout_year']})")
            st.markdown("**Experience**")
            st.write(f"{p['job_title'] or 'N/A'} ({p['experience']})")
        with c2:
            st.markdown("**Skills**")
            st.write(", ".join(p["technical_skills"]) or "—")
            st.markdown("**Projects**")
            st.write(", ".join(p["projects"]) or "—")
            st.markdown("**Certifications**")
            st.write(", ".join(p["certifications"]) or "—")
 
# ----- Tab 3: jobs ----- #
with tab_jobs:
    if "profile" not in st.session_state:
        st.info("Generate your resume first, then search for matching jobs here.")
    else:
        p = st.session_state.profile
        st.write(f"Searching for **{p['preferred_job_role']}** roles that fit your profile.")
        if st.button("🔎 Find Live Jobs", type="primary"):
            try:
                with st.spinner("AI is searching the web for open jobs (this can take 1-2 minutes)..."):
                    st.session_state.jobs = find_jobs_online(p, limit=job_limit)
            except Exception as e:  # noqa: BLE001
                st.error(f"Job search failed: {e}")
 
        jobs = st.session_state.get("jobs")
        if jobs is not None:
            if not jobs:
                st.warning("No matching jobs found right now. Try different keywords or locations.")
            else:
                st.download_button("⬇️ Export jobs as CSV", jobs_to_csv(jobs),
                                   file_name="job_recommendations.csv", mime="text/csv")
                for j in jobs:
                    match = int(j.get("match_percent") or 0)
                    with st.container(border=True):
                        left, right = st.columns([4, 1])
                        left.subheader(j.get("title", "Untitled role"))
                        left.caption(
                            f"🏢 {j.get('company', 'N/A')}  ·  📍 {j.get('location', 'N/A')}  ·  "
                            f"💰 {j.get('salary') or 'N/A'}  ·  🌐 {j.get('source_site', 'N/A')}"
                        )
                        right.metric("Match", f"{match}%")
                        st.progress(min(max(match, 0), 100) / 100)
                        if j.get("reason"):
                            st.write(j["reason"])
                        if j.get("matching_skills"):
                            st.markdown("✅ **Matching:** " + ", ".join(j["matching_skills"]))
                        if j.get("missing_skills"):
                            st.markdown("📚 **To learn:** " + ", ".join(j["missing_skills"]))
                        if j.get("apply_url"):
                            st.link_button("Apply now ↗", j["apply_url"])
 