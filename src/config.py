"""
Central configuration for Internship Radar.

Loads environment variables (.env), defines file paths, status/category
options, and the user profile text used when asking OpenAI to score a job's
fit. Keeping all of this in one place makes the rest of the app easier to
read and easier to tweak later.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# --- Paths -------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "internships.db"

# Load variables from a .env file in the project root, if present.
load_dotenv(BASE_DIR / ".env")

# --- OpenAI --------------------------------------------------------------

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- Job status workflow --------------------------------------------------

STATUS_OPTIONS = [
    "New",
    "Viewed",
    "Interested",
    "Applied",
    "Interview",
    "Rejected",
    "Not Interested",
    "Closed",
]
DEFAULT_STATUS = "New"

# Statuses selectable from the Viewed Jobs page (a deliberately narrower set --
# you've already seen the job, so "New"/"Viewed" aren't useful next steps there).
VIEWED_PAGE_STATUS_OPTIONS = [
    "Interested",
    "Applied",
    "Not Interested",
    "Rejected",
    "Closed",
]

# --- Role categories -------------------------------------------------------

ROLE_CATEGORIES = [
    "Software Engineering",
    "AI / ML",
    "Data Science",
    "Cloud",
    "Cybersecurity",
    "Backend",
    "Other",
]

# Keywords used to bucket a job title/description into a role category.
# Checked in order, first match wins.
ROLE_CATEGORY_KEYWORDS = [
    ("AI / ML", ["ai engineer", "machine learning", "ml engineer", " ai ", "artificial intelligence"]),
    ("Data Science", ["data scientist", "data science"]),
    ("Cybersecurity", ["cyber", "security", "infosec", "soc analyst"]),
    ("Cloud", ["cloud", "devops", "azure", "aws", "gcp", "infrastructure"]),
    ("Backend", ["backend", "back-end", "back end", "api engineer", "server-side"]),
    ("Software Engineering", ["software engineer", "software engineering", "swe", "developer", "full stack", "full-stack"]),
]

# --- Dashboard thresholds --------------------------------------------------

HIGH_FIT_SCORE_THRESHOLD = 80

# --- User fit profile -------------------------------------------------------
# This text is fed to OpenAI (and used for fallback keyword scoring) so
# scoring reflects the actual student's background and goals.

USER_PROFILE = """
JMU Computer Science student looking for a Summer 2027 internship.
Interested in software engineering, AI engineering, data science, cloud
engineering, cybersecurity, backend development, and general coding
internships. Prefers roles in Northern Virginia, Washington DC, remote,
New York City, or at strong, well-known tech companies.

Experience: Azure, Power BI, cybersecurity dashboards, Tenable API data,
IT support, RPA (robotic process automation) documentation, Salesforce
development, and internal application development.

Wants a role with meaningful, hands-on engineering work rather than
administrative or purely observational tasks.
""".strip()

# Keyword list used by the fallback (no API key) scorer. Grouped loosely by
# topic so we can also surface which skills matched a given posting.
FALLBACK_SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "sql",
    "backend", "back-end", "full stack", "full-stack", "api", "rest",
    "cloud", "azure", "aws", "gcp", "devops", "kubernetes", "docker",
    "machine learning", "ai", "artificial intelligence", "data science",
    "data", "analytics", "power bi", "tableau",
    "cybersecurity", "security", "soc", "tenable", "vulnerability",
    "salesforce", "rpa", "automation", "software engineer", "developer",
    "remote", "internship",
]

# --- Link validity -------------------------------------------------------
# Substrings that mark a URL as fake/placeholder/broken. Checked as a
# case-insensitive substring match against the whole URL.
PLACEHOLDER_URL_MARKERS = [
    "example.com",
    "/404",
    "placeholder",
    "fake",
    "todo",
    "company.com",
]

# Known-good top-level careers pages, keyed by normalized company name
# (see src.dedupe.normalize_text). Used to (a) populate sample job URLs with
# real, working links instead of guessed posting paths, and (b) repair any
# previously-saved placeholder URLs. Each of these was confirmed reachable
# (direct fetch, or a genuine server-issued redirect to the company's
# applicant-tracking system) rather than guessed.
COMPANY_CAREERS_URLS = {
    "capital one": "https://www.capitalonecareers.com/",
    "microsoft": "https://careers.microsoft.com/",
    "navy federal credit union": "https://www.navyfederal.org/about/careers.html",
    "booz allen hamilton": "https://www.boozallen.com/careers.html",
    "leidos": "https://www.leidos.com/careers",
    "northrop grumman": "https://www.northropgrumman.com/careers/",
    "palantir": "https://www.palantir.com/careers/",
    "greystone": "https://www.greystone.com/careers/",
}
