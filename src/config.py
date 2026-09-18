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

# Query-string parameters known to be tracking/attribution noise (added by
# email campaigns, social shares, job-board referral links, etc.) rather
# than part of what identifies a specific posting. Stripped during URL
# normalization for dedupe -- see src.dedupe.normalize_url. Deliberately a
# denylist, not an allowlist: a param we've never seen before (e.g. a
# Greenhouse `gh_jid` or Lever job id embedded in the query string) is kept
# by default so two genuinely different postings never collapse into one
# just because of an unfamiliar param name.
TRACKING_QUERY_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "gh_src", "gh_jobboard", "gh_medium", "lever-source",
    "lever-origin", "ref", "referrer", "source", "src", "fbclid", "gclid",
    "msclkid", "mc_cid", "mc_eid", "trk", "li_fat_id",
}

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
#
# Last verified live against the real boards-api.greenhouse.io / api.lever.co
# endpoints on 2026-09-18. Six of the original twelve tokens had gone stale
# (404): Snowflake, DoorDash, Affirm, Plaid, Netflix, and Rippling. DoorDash
# and Affirm were recovered with corrected tokens ("doordashusa", and a move
# from Lever to Greenhouse under the same "affirm" token, both confirmed by
# the API's own `company_name` field and a live redirect from
# boards.greenhouse.io/<token>). Snowflake, Plaid, Netflix, and Rippling no
# longer expose a public Greenhouse/Lever board at all (they've moved to an
# ATS this collector doesn't support, e.g. Workday) and were replaced with
# Lyft, Dropbox, Figma, and Scale AI -- all confirmed live with real Summer
# 2027 software/data internship postings at verification time.
BOARD_SOURCES = [
    {"company": "Stripe", "board": "greenhouse", "token": "stripe"},
    {"company": "Airbnb", "board": "greenhouse", "token": "airbnb"},
    {"company": "Robinhood", "board": "greenhouse", "token": "robinhood"},
    {"company": "Coinbase", "board": "greenhouse", "token": "coinbase"},
    {"company": "Databricks", "board": "greenhouse", "token": "databricks"},
    {"company": "Lyft", "board": "greenhouse", "token": "lyft"},
    {"company": "Asana", "board": "greenhouse", "token": "asana"},
    {"company": "DoorDash", "board": "greenhouse", "token": "doordashusa"},
    {"company": "Affirm", "board": "greenhouse", "token": "affirm"},
    {"company": "Dropbox", "board": "greenhouse", "token": "dropbox"},
    {"company": "Figma", "board": "greenhouse", "token": "figma"},
    {"company": "Scale AI", "board": "greenhouse", "token": "scaleai"},
]

# Postings must look like an internship/co-op (title match, checked as
# whole words -- see src.text_match) AND look relevant to the student's
# target roles (title/description match) AND NOT look like an unrelated
# sales/marketing/legal/HR role (title match) to be kept.
#
# Title is the primary evidence for "is this actually an internship" --
# real ATS postings almost always say "Intern"/"Internship"/"Co-op" in the
# title itself, and requiring it there (rather than allowing an incidental
# mention buried in the description, e.g. "you'll work alongside our
# summer interns") is what keeps a full-time role from being misclassified
# just because its description happens to reference interns.
#
# All matching here uses whole-word boundaries (src.text_match), not plain
# substring checks -- plain substring matching on "intern" was the actual
# root cause of real false positives observed when this list was checked
# against live Greenhouse data: "Internal Tools Engineer", "Director,
# International Tax", and "Database Internals" all contain "intern" as a
# substring but are not internships.
INTERNSHIP_TITLE_KEYWORDS = ["intern", "interns", "internship", "internships", "co-op", "coop"]

# Title keywords that mark a posting as an unrelated role even if it's a
# genuine internship and even if its description happens to mention
# software/engineering teams (e.g. a "Sales Development Intern" whose blurb
# says "partner closely with our engineering team"). Checked against the
# title only, and takes priority over RELEVANT_POSTING_KEYWORDS below.
EXCLUDED_TITLE_KEYWORDS = [
    "sales", "account executive", "account manager", "account development",
    "business development", "marketing", "communications", "public relations",
    "legal", "paralegal", "attorney", "counsel", "human resources",
    "recruiting", "recruiter", "talent acquisition", "people operations",
    "finance intern", "accounting intern", "audit", "procurement",
    "supply chain", "merchandising", "retail", "hospitality",
]

RELEVANT_POSTING_KEYWORDS = [
    "software", "engineer", "engineering", "developer", "dev",
    "data", "machine learning", "ml", "ai", "artificial intelligence",
    "cloud", "devops", "infrastructure", "backend", "back-end", "full stack",
    "full-stack", "security", "cyber", "platform", "systems", "technical",
]
