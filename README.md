# Internship Radar

A local dashboard for discovering and tracking **Summer 2027** software engineering, AI
engineering, machine learning, data science, cloud, and cybersecurity internships.

Internship Radar runs entirely on your own laptop. There is no cloud hosting, no
authentication, and no background scheduler in this first version -- you open the app and
click **Refresh Jobs** whenever you want new postings pulled in, scored, and saved.

## What this project is

- A Streamlit dashboard backed by a local SQLite database.
- A "Refresh Jobs" button that collects internship postings, deduplicates them against
  what's already saved, scores each new posting for fit, and updates the dashboard.
- A place to track your own status on each posting (New, Viewed, Interested, Applied,
  Interview, Rejected, Not Interested, Closed) and keep notes.

## Tech stack

- Python
- Streamlit (UI)
- SQLite (storage)
- OpenAI API (optional AI scoring, with a keyword-based fallback)
- requests / beautifulsoup4 (collectors)
- pandas (data handling)
- python-dotenv (loading your API key from `.env`)

## Project structure

```text
Internship Radar/
  app.py                        # Streamlit dashboard (UI + page logic)
  requirements.txt
  .env.example
  data/
    internships.db              # created automatically on first run
  src/
    config.py                   # paths, statuses, categories, user profile, careers-URL map
    db.py                       # SQLite schema + CRUD + placeholder-URL cleanup
    ranker.py                   # OpenAI scoring + keyword fallback
    dedupe.py                   # URL / company+title+location dedupe logic
    urls.py                     # link validation + trust level (Verified/Missing/Needs Review)
    collectors/
      sample_source.py          # static sample postings (used today)
      github_sources.py         # scaffold for a future GitHub-based source
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

## What this first version does

1. Click **Refresh Jobs** on the Dashboard.
2. The app collects sample internship postings (Capital One, Microsoft, Palantir, Booz
   Allen Hamilton, Leidos, Northrop Grumman, Navy Federal, Greystone, and more) across
   software engineering, AI/ML, data science, cloud, and cybersecurity roles.
3. Postings are deduplicated by URL (or by normalized company + title + location if a
   posting has no URL) so refreshing repeatedly doesn't create duplicate rows.
4. New postings are saved to a local SQLite database (`data/internships.db`).
5. Each new posting is scored 0-100 for fit against your profile -- via OpenAI if a key
   is configured, or a transparent keyword-overlap score if not.
6. The dashboard shows metric cards (New Roles, High-Fit Roles, Viewed Jobs, Applied,
   Interviews), a **Top Internship Matches** card view, and (on the All Internships page)
   filters plus a sortable table of every stored job with clickable posting links.
7. Select any job to update its status or add notes -- changes save back to SQLite, and
   opening a job's detail view automatically marks it viewed.
8. Use **Applied Tracker** to see everything you've applied to, and **Viewed Jobs** to
   revisit postings you've already looked at.

## A note on posting links

Sample data is illustrative, not scraped from a live job board, so there's no exact
posting URL for it to link to. Each sample job's link points to that company's real,
verified **careers page** (see `COMPANY_CAREERS_URLS` in `src/config.py`) rather than a
guessed posting path -- guessed paths like `.../internships/software-engineering-2027`
don't actually exist and just 404. The table's **Link Status** column reflects this
honestly:

- **Verified** -- an exact posting URL from a real collector
- **Needs Review** -- a valid link, but only a general company careers page (today, this
  is every sample job)
- **Missing** -- no usable link at all

Every link is checked with `is_valid_url()` (`src/urls.py`) before it's ever rendered.
Empty, malformed, or placeholder-looking URLs (containing things like `/404`,
`example.com`, or `placeholder`) are never shown as clickable -- the UI displays
**"No verified link"** instead. A one-time cleanup (`db.clean_placeholder_urls()`) also
repairs or clears any bad URLs left over from an earlier version of the sample data, the
first time you run the updated app. When a real collector (like `github_sources.py`,
once it's wired up) provides an exact posting URL, that URL is used as-is and is never
overwritten by the cleanup step.

## Planned future improvements

- Wire up `src/collectors/github_sources.py` to a real, actively-maintained GitHub
  internship listing repo (it's currently scaffolded but not called automatically).
- Add more live sources (company career pages, job boards) behind the same dedupe/scoring
  pipeline.
- Optional local scheduling (e.g. run refresh automatically once a day) once the manual
  workflow feels solid.
- Export to CSV / Google Sheets for sharing an application tracker with mentors or peers.
- Basic analytics (application funnel over time, response rate by company/category).
