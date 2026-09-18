# Internship Radar

A local dashboard for discovering and tracking **Summer 2027** software engineering, AI
engineering, machine learning, data science, cloud, and cybersecurity internships.

Internship Radar runs entirely on your own laptop. There is no cloud hosting, no
authentication, and no background scheduler -- you open the app and click **Refresh Jobs**
whenever you want new postings pulled in, scored, and saved.

## What this project is

- A Streamlit dashboard backed by a local SQLite database.
- A **Refresh Jobs** button that collects real internship postings from each configured
  company's live Greenhouse/Lever job board, deduplicates them against what's already
  saved, scores each new posting for fit, and updates the dashboard.
- A place to track your own status on each posting (New, Viewed, Interested, Applied,
  Interview, Rejected, Not Interested, Closed) and keep notes.

## Tech stack

- Python
- Streamlit (UI)
- SQLite (storage)
- OpenAI API (optional AI scoring, with a keyword-based fallback)
- requests (live Greenhouse/Lever job board APIs)
- pandas (data handling)
- python-dotenv (loading your API key from `.env`)
- pytest (automated test suite)

## Project structure

```text
Internship Radar/
  app.py                        # Streamlit dashboard (UI + page logic)
  requirements.txt
  requirements-dev.txt          # + pytest, for running the test suite
  pytest.ini
  .env.example
  data/
    internships.db              # created automatically on first run
    last_refresh.json           # per-source stats from the last refresh (safe to delete)
  src/
    config.py                   # paths, statuses, categories, user profile, board sources
    db.py                       # SQLite schema + migrations + CRUD
    ranker.py                   # OpenAI scoring + keyword fallback
    dedupe.py                   # URL / company+title+location dedupe logic
    urls.py                     # link validation + trust level (Verified/Missing/Needs Review)
    season.py                   # Summer 2027 season/year classification
    text_match.py                # shared whole-word keyword matching
    refresh_state.py            # persists "what happened on the last refresh"
    collectors/
      board_apis.py             # live Greenhouse/Lever collector (the default source)
      sample_source.py          # static illustrative postings (opt-in demo data)
      github_sources.py         # scaffold for a future GitHub-based source (not wired in)
  scripts/
    verify_boards.py            # checks every configured board against the real API
  tests/                        # pytest suite (temp DBs + mocked network only)
```

## Install

From inside the `Internship Radar` folder:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

(If you're not using a virtual environment, you can skip the first two lines and just run
`pip install -r requirements.txt` directly.)

To also run the test suite, install the dev requirements instead (it includes everything in
`requirements.txt` plus `pytest`):

```bash
pip install -r requirements-dev.txt
```

## Set up your `.env` file

Copy the example file and add your own OpenAI API key:

```bash
copy .env.example .env
```

Then open `.env` and replace the placeholder:

```env
OPENAI_API_KEY=your_api_key_here
```

**You do not need an API key to use the app.** If `OPENAI_API_KEY` is missing or blank,
Internship Radar automatically falls back to a keyword-based scoring method so the app is
always usable.

## Run the app

```bash
streamlit run app.py
```

Streamlit will open the dashboard in your browser (usually at `http://localhost:8501`).

## How it actually works today

### Real postings by default, sample data explicitly opt-in

Clicking **Refresh Jobs** pulls live postings directly from each configured company's public
Greenhouse or Lever job board API (`src/collectors/board_apis.py`, tokens listed in
`src/config.py`'s `BOARD_SOURCES`) -- no scraping, no API key required, since both of those
board providers expose stable, unauthenticated JSON endpoints for their public postings.
This is the default, real-postings experience.

Static, illustrative sample postings (`src/collectors/sample_source.py`) are **never**
included by default. Check **Include sample / demo data** in the sidebar to (a) pull sample
postings in on the next refresh and (b) show any sample rows already in the database. Sample
rows are always tagged with a **Sample / Demo** badge everywhere they appear, and a separate
"Data Type" column in the All Internships table makes them easy to filter out. Turning the
toggle back off never deletes sample rows -- it just hides them again.

### Filtering: what counts as a relevant Summer 2027 internship

A live posting is kept only if **all** of the following hold (`board_apis._looks_like_relevant_internship`):

1. **Its title** contains an internship/co-op word ("intern", "internship", "co-op") as a
   whole word, not a substring. This is checked with word-boundary matching
   (`src/text_match.py`), not plain substring matching -- plain substring matching was the
   actual root cause of real false positives found while wiring this up against live
   Greenhouse data: "Internal Tools Engineer", "Director, International Tax", and
   "Database Internals" all contain "intern" as a substring but are not internships. A
   description merely *mentioning* interns (e.g. "you'll mentor our summer interns") no
   longer qualifies a full-time role, because only the title is used as internship
   evidence.
2. **Its title** does **not** match an excluded-role keyword (sales, marketing, legal,
   HR/recruiting, business development, finance/accounting, audit, retail, etc. -- see
   `EXCLUDED_TITLE_KEYWORDS` in `src/config.py`). This is checked before relevance, so a
   "Sales Development Intern" whose blurb happens to say "partner with our engineering
   team" is still excluded.
3. **Its title or description** contains at least one relevant-role keyword (software,
   engineer, data, cloud, security, etc.), also whole-word matched.
4. **Its season/year isn't explicitly incompatible** with Summer 2027 (see below) -- an
   otherwise-relevant "Summer 2026" or "Fall 2027" posting is filtered out here, before it
   ever reaches the database.

### Season handling -- Summer 2027, never invented

Every kept posting is classified by `src/season.py` into one of:

- **Summer 2027 (confirmed)** -- the text explicitly says "Summer 2027" (or an equivalent
  phrasing: "2027 Summer", "Summer '27", etc.).
- **incompatible** -- the text explicitly names a different season and/or year (e.g.
  "Summer 2026", "Fall 2027", "2026 Internship Program"). These are dropped by the collector
  and never saved.
- **Season unconfirmed** -- no clear season/year signal in the text at all. These postings
  are **kept** (most real postings don't repeat "Summer 2027" verbatim in the title), and
  clearly labeled "Season unconfirmed" everywhere in the UI, with an independent **Season**
  filter on the All Internships page to show or hide them. The app never invents a season --
  a posting that only says "2027" with no season word attached stays "unconfirmed" rather
  than being upgraded to a confirmed Summer 2027 match.

This is a conservative, regex-based heuristic over free text (see `src/season.py`'s
docstring), not a real date parser -- it won't catch every phrasing a company might use.
That's an accepted, documented limitation.

### Dates: four different things, kept separate

Each job tracks four distinct timestamps, and the UI never conflates them:

- **Posted** -- the source's own original publication date, only ever set from a field that
  actually represents one (Lever's `createdAt`, or Greenhouse's `first_published` when a
  board provides it). Greenhouse's `updated_at` is **not** used for this -- it reflects the
  last time the listing was edited, which can be nothing more than a metadata tweak, and
  using it as a "posted" date would misrepresent how old a posting actually is.
- **Source updated** -- the source system's own "last modified" timestamp (Greenhouse's
  `updated_at` / Lever's `updatedAt`), stored separately so it's never confused with a
  publication date.
- **Discovered** -- when *this app* first saw the posting. Set once, on insert, and never
  changed.
- **Last seen** -- when *this app* most recently saw the posting still listed by its source.
  Bumped every refresh that finds it again.

The All Internships sort dropdown is labeled to match: **Best fit first** (score),
**Recently posted first** (posted date, blank ones sort last), **Recently discovered first**
(when you first found it), **Company A-Z**.

### Deduplication that survives repeated refreshes

Postings are deduplicated primarily by URL (`src/dedupe.py`). URL normalization strips a
denylist of known *tracking* query parameters (`utm_*`, `gh_src`, `fbclid`, etc. -- see
`TRACKING_QUERY_PARAMS` in `src/config.py`) but preserves any other query parameter, since a
board's only way of identifying *which* posting a link points to sometimes lives in the
query string (e.g. a Greenhouse embed's `?gh_jid=...`). Dropping every query param
unconditionally risked silently collapsing two different postings into one "duplicate."

Sample-source jobs (which all point at one company careers page, not a per-posting URL) are
keyed on normalized company + title + location instead, so distinct sample postings from the
same company never collapse into each other.

Re-running Refresh Jobs never creates duplicate rows and never overwrites anything you've
set yourself (status, notes, the viewed flag, score) -- a posting seen again just gets its
`last_seen_at` bumped. This is covered by `tests/test_db.py`.

### Live-source reliability

Every board fetch is isolated (`src/collectors/board_apis.py`): a bad/renamed token, a
network timeout, or a malformed JSON response for one company is caught and recorded, never
raised, and never stops the other configured sources from coming through. A 10-second
timeout is used per request.

An unavailable source is never displayed as if it were a successful search that just found
zero postings -- the Settings page shows each source's real status (a count of relevant
postings found, or the specific error, in red, if it couldn't be reached), and the Dashboard
surfaces a warning banner naming how many of the configured sources were unavailable on the
last refresh.

Run `python scripts/verify_boards.py` any time to check every configured board token
against the real public API directly (needs normal internet access):

```bash
python scripts/verify_boards.py
```

**Board sources were last verified live on 2026-09-18.** Six of the original twelve
configured tokens had gone stale (404 from the real API): Snowflake, DoorDash, Affirm,
Plaid, Netflix, and Rippling. DoorDash and Affirm were recovered with corrected tokens
(DoorDash moved to `doordashusa`; Affirm moved from Lever to Greenhouse under the same
`affirm` token) -- both confirmed via the API's own `company_name` field and a live redirect
from `boards.greenhouse.io/<token>`, not guessed. Snowflake, Plaid, Netflix, and Rippling no
longer expose a public Greenhouse/Lever board at all (they've moved to an ATS this collector
doesn't support, most likely Workday) and were replaced with Lyft, Dropbox, Figma, and Scale
AI, each confirmed live with real Summer 2027 software/data internship postings at
verification time. All 12 currently configured sources resolved successfully as of that
check.

## A note on posting links

Sample data is illustrative, not scraped from a live job board, so there's no exact posting
URL for it to link to. Each sample job's link points to that company's real, verified
**careers page** (see `COMPANY_CAREERS_URLS` in `src/config.py`) rather than a guessed
posting path. Live board postings always use the exact posting URL returned by the source
API. The table's **Link Status** column reflects this honestly:

- **Verified** -- an exact posting URL from a real collector
- **Needs Review** -- a valid link, but only a general company careers page (sample/demo
  data only)
- **Missing** -- no usable link at all

Every link is checked with `is_valid_url()` (`src/urls.py`) before it's ever rendered.
Empty, malformed, or placeholder-looking URLs are never shown as clickable.

## Testing

Automated tests (`tests/`) never touch your real database and never call a paid API -- every
test that needs a database uses a throwaway temp SQLite file (`tests/conftest.py`), and the
ranker tests exercise the keyword-fallback scorer directly rather than `rank_job()`/the
OpenAI client, regardless of what's in your `.env`.

```bash
pip install -r requirements-dev.txt
pytest
```

Coverage includes: whole-word keyword matching (the "internal"/"international" false-positive
fix), season classification (confirmed/incompatible/unconfirmed, including the "never invent
a season" rule), title-based relevance/exclusion filtering (sales/marketing/legal roles,
description-only intern mentions), Greenhouse/Lever date-field handling (`posted_at` vs
`source_updated_at`), network error and malformed-JSON isolation, URL/tracking-param
normalization and dedupe, database migration safety, and preservation of user-set
status/notes/score across repeated refreshes.

Live-source connectivity is intentionally **not** part of the automated suite (it needs real
internet access and real third-party APIs that can change independently of this code) --
run `python scripts/verify_boards.py` separately for that, as described above.

The Streamlit UI itself (`app.py`) was smoke-tested end-to-end using Streamlit's official
`AppTest` headless testing framework against an isolated copy of the app (separate database,
blanked API key) -- refresh, the sample-data toggle, season/source filters, sorting, the job
detail editor (status change + notes), Applied Tracker, Viewed Jobs, Settings, and a repeated
refresh confirming no duplicates and preserved notes were all exercised this way. `app.py`'s
UI-layer functions aren't covered by the `tests/` pytest suite directly (they're Streamlit
script code, not easily unit-testable in isolation without a larger refactor) -- this is a
known, documented gap; the logic-heavy modules under `src/` where the real filtering/season/
dedupe/date bugs lived have full unit coverage instead.

## Known limitations

- Season detection is a regex heuristic over free text, not a real date parser -- unusual
  phrasing may be missed and will fall into "Season unconfirmed" rather than being wrongly
  classified. This is by design (never invent a date), but it does mean the "Season
  unconfirmed" filter will sometimes include postings a human would recognize as Summer 2027.
- Only Greenhouse and Lever boards are supported. Companies on other ATS platforms (Workday,
  Ashby, iCIMS, SmartRecruiters, custom career sites) aren't collected from yet.
- `src/collectors/github_sources.py` remains a scaffold, not wired into the default refresh.
- There's no background scheduler -- refresh is always a manual, on-demand action.

## Planned future improvements

- Wire up `src/collectors/github_sources.py` to a real, actively-maintained GitHub
  internship listing repo.
- Add collectors for additional ATS platforms (Workday, Ashby, etc.) behind the same
  dedupe/scoring pipeline.
- Optional local scheduling (e.g. run refresh automatically once a day) once the manual
  workflow feels solid.
- Export to CSV / Google Sheets for sharing an application tracker with mentors or peers.
- Basic analytics (application funnel over time, response rate by company/category).
