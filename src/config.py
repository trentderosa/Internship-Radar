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

# --- Location fit -----------------------------------------------------------
# Substrings (case-insensitive) that mark a posting's location as a strong
# geographic fit for the student's stated preferences (Northern Virginia /
# DC metro, NYC, or remote). Used by the ranker as a scoring bonus and by the
# UI to explain *why* a job scored the way it did.
PREFERRED_LOCATION_KEYWORDS = [
    "remote",
    "washington, dc", "washington dc", "d.c.",
    "arlington", "mclean", "vienna", "reston", "tysons", "fairfax",
    "alexandria", "herndon", "chantilly", "northern virginia", "nova",
    "new york",
]

# --- Real job board sources --------------------------------------------------
# Curated list of companies whose public applicant-tracking-system job boards
# are queried directly (no scraping/HTML parsing -- Greenhouse and Lever both
# expose stable, unauthenticated JSON APIs for their public job boards).
#
# IMPORTANT: `token` is the identifier the company uses in its own board URL
# (e.g. boards.greenhouse.io/<token> or jobs.lever.co/<token>), and it does
# NOT always match the company's public brand name. These were set from
# publicly known board URLs, but companies do rename/migrate ATS providers
# over time, so a token can go stale. Run `python scripts/verify_boards.py`
# (needs normal internet access) after pulling this to see which of these
# currently resolve, and prune/replace any that don't -- see that script's
# docstring for how to find a company's current token by hand.
BOARD_SOURCES = [
    {"company": "Stripe", "board": "greenhouse", "token": "stripe"},
    {"company": "Airbnb", "board": "greenhouse", "token": "airbnb"},
    {"company": "Robinhood", "board": "greenhouse", "token": "robinhood"},
    {"company": "Coinbase", "board": "greenhouse", "token": "coinbase"},
    {"company": "Databricks", "board": "greenhouse", "token": "databricks"},
    {"company": "Snowflake", "board": "greenhouse", "token": "snowflake"},
    {"company": "Asana", "board": "greenhouse", "token": "asana"},
    {"company": "DoorDash", "board": "greenhouse", "token": "doordash"},
    {"company": "Affirm", "board": "lever", "token": "affirm"},
    {"company": "Plaid", "board": "lever", "token": "plaid"},
    {"company": "Netflix", "board": "lever", "token": "netflix"},
    {"company": "Rippling", "board": "lever", "token": "rippling"},
]

# Postings must look like an internship (title match) AND look relevant to
# the student's target roles (title/description match) to be kept -- this
# keeps a company's sales/marketing/legal internships out of the results.
INTERNSHIP_TITLE_KEYWORDS = ["intern", "internship", "co-op", "coop"]
RELEVANT_POSTING_KEYWORDS = [
    "software", "engineer", "engineering", "developer", "dev ",
    "data", "machine learning", "ml ", "ai ", "artificial intelligence",
    "cloud", "devops", "infrastructure", "backend", "back-end", "full stack",
    "full-stack", "security", "cyber", "platform", "systems", "technical",
]
