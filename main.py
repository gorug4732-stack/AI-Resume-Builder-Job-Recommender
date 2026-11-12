import json
import os
import re
import smtplib
import requests
import ssl
from pathlib import Path
from email.message import EmailMessage
from io import BytesIO
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"), override=True)

from openai import OpenAI
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (HRFlowable, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

# ---------------- Config ---------------- #

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
CHAT_MODEL = "gpt-5-nano"        # details collect karne ke liye
SEARCH_MODEL = "gpt-5-mini"      # web search ke liye (web_search tool support karne wala model)

# ---------------- Step 1: Collect details ---------------- #

system_prompt = """
You are an AI Resume Builder Assistant.
Your primary responsibility is to collect the user's information.

Rules:
1. Ask ONLY ONE question at a time.
2. Wait for the user's answer before asking the next question.
3. Do not assume any information.
4. If the answer is incomplete or invalid, politely ask for clarification.
5. Keep the conversation short and professional.
6. Remember all previous answers.
7. After collecting every field, return ONLY the JSON object.

Collect in this exact order:
1. Full Name (first name compulsory, last name optional)
2. Email Address (proper email format)
3. Phone Number (exactly 10 digits)
4. Highest Qualification
5. Degree / Course
6. College / University Name 
7. Graduation / Passout Year
8. Current Experience (a single number means years; don't ask for a format)
9. Current / Previous Job Title
10. Technical Skills
11. Projects Completed (only project names, comma separated)
12. Certifications
13. Preferred Job Role
14. Preferred Job Locations
15. Expected Salary

After collecting all, return ONLY this JSON:
{
  "output": {
    "name":"", "email":"", "phone":"", "qualification":"", "degree":"",
    "college":"", "passout_year":"", "experience":"", "job_title":"",
    "technical_skills":[], "projects":[], "certifications":[],
    "preferred_job_role":"", "preferred_locations":[], "expected_salary":""
  }
}
"""


def extract_json(text):
    """Reply me se pehla valid JSON object nikalta hai."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON found")
    return json.loads(text[start:end + 1])


def collect_user_details():
    messages = [{"role": "system", "content": system_prompt}]
    print("=" * 60)
    print("     AI Resume Builder & Live Job Recommendation")
    print("=" * 60)

    while True:
        response = client.chat.completions.create(model=CHAT_MODEL, messages=messages)
        reply = response.choices[0].message.content.strip()
        messages.append({"role": "assistant", "content": reply})

        if '"output"' in reply:
            try:
                return extract_json(reply)["output"]
            except Exception as e:
                print("JSON parse error, retrying:", e)
                messages.append({"role": "user", "content": "Return ONLY valid JSON."})
                continue

        print("\nAssistant:", reply)
        messages.append({"role": "user", "content": input("\nYou : ")})


# ---------------- Step 2: Resume PDF ---------------- #

ACCENT = colors.HexColor("#1a4d8f")
GREY = colors.HexColor("#555555")


def _styles():
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle("Name", parent=base["Title"], fontSize=22, leading=26,
                               textColor=ACCENT, alignment=TA_CENTER, spaceAfter=2),
        "contact": ParagraphStyle("Contact", parent=base["Normal"], fontSize=9, leading=13,
                                  textColor=GREY, alignment=TA_CENTER, spaceAfter=8),
        "section": ParagraphStyle("Section", parent=base["Heading2"], fontSize=12, leading=15,
                                  textColor=ACCENT, spaceBefore=8, spaceAfter=3),
        "body": ParagraphStyle("Body", parent=base["Normal"], fontSize=10, leading=14),
        "bullet": ParagraphStyle("Bullet", parent=base["Normal"], fontSize=10, leading=14,
                                 leftIndent=12, bulletIndent=2),
    }


def _section(title, styles):
    return [Paragraph(title.upper(), styles["section"]),
            HRFlowable(width="100%", thickness=0.8, color=ACCENT, spaceAfter=5)]


def build_resume_pdf(p):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)
    s = _styles()
    story = [Paragraph(p["name"], s["name"]),
             Paragraph(f'{p["phone"]} | {p["email"]}', s["contact"])]

    story += _section("Career Objective", s)
    story.append(Paragraph(
        f"Seeking a position as {p['preferred_job_role']} where I can utilize my skills "
        f"and grow professionally.", s["body"]))

    story += _section("Education", s)
    rows = [["Degree", "Institute", "Year"],
            [p["degree"], p["college"], p["passout_year"]]]
    table = Table(rows, colWidths=[60 * mm, 75 * mm, 30 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
    ]))
    story.append(table)

    if p.get("technical_skills"):
        story += _section("Technical Skills", s)
        for sk in p["technical_skills"]:
            story.append(Paragraph(sk, s["bullet"], bulletText="•"))

    if p.get("projects"):
        story += _section("Projects", s)
        for pr in p["projects"]:
            story.append(Paragraph(pr, s["bullet"], bulletText="•"))
            story.append(Spacer(1, 2))

    if p.get("job_title"):
        story += _section("Experience", s)
        story.append(Paragraph(f'{p["job_title"]} ({p["experience"]})', s["body"]))

    if p.get("certifications"):
        story += _section("Certifications", s)
        for c in p["certifications"]:
            story.append(Paragraph(c, s["bullet"], bulletText="•"))

    doc.build(story)
    return buffer.getvalue()


# ---------------- Step 3: AI web search se live jobs ---------------- #

def find_jobs_online(p, limit=5):
    """AI internet par khud search karke real jobs dhoondta hai."""
    prompt = f"""
You are a job search assistant. Use web search to find CURRENT, REAL, OPEN job
listings on websites like Naukri, LinkedIn, Indeed, Glassdoor, Internshala,
Foundit or company career pages.

Candidate profile:
{json.dumps(p, indent=2)}

Rules:
1. Find the best {limit} jobs matching the candidate's preferred role, skills,
   experience level and preferred locations (remote is fine too).
2. Every job MUST have a real, working apply URL taken from the search results.
   Never invent jobs, companies or links. If you find fewer, return fewer.
3. Estimate match_percent (0-100) honestly from skills/experience fit.
4. Return ONLY valid JSON, no extra text, in this format:

{{"jobs":[
  {{"title":"","company":"","location":"","salary":"","experience":"",
    "source_site":"","apply_url":"","match_percent":0,
    "matching_skills":[],"missing_skills":[],"reason":""}}
]}}
"""
    response = client.responses.create(
        model=SEARCH_MODEL,
        tools=[{"type": "web_search"}],
        input=prompt,
    )
    data = extract_json(response.output_text)
    jobs = data.get("jobs", [])
    jobs.sort(key=lambda j: j.get("match_percent", 0), reverse=True)
    return jobs[:limit]


def format_jobs_text(jobs):
    if not jobs:
        return "No matching jobs found right now."
    lines = []
    for i, j in enumerate(jobs, 1):
        lines.append(
            f"{i}. {j['title']} - {j['company']} ({j['match_percent']}% match)\n"
            f"   Location: {j['location']} | Salary: {j.get('salary') or 'N/A'}\n"
            f"   Why: {j['reason']}\n"
            f"   Apply: {j['apply_url']}\n")
    return "\n".join(lines)


# ---------------- Main ---------------- #

if __name__ == "__main__":
    prefs = collect_user_details()
    print("\nProfile collected:\n", json.dumps(prefs, indent=2))

    pdf_bytes = build_resume_pdf(prefs)
    with open("Generated_Resume.pdf", "wb") as f:
        f.write(pdf_bytes)
    print("\nResume saved: Generated_Resume.pdf")

    print("\n-------- Searching Jobs On Internet --------")
    jobs = find_jobs_online(prefs)

    print("\n" + "=" * 70)
    print("---------- TOP AI-FOUND JOB RECOMMENDATIONS ----------")
    print("=" * 70)
    print(format_jobs_text(jobs))
