"""
Job fit scoring.

Two scoring paths:
1. OpenAI-based scoring (used when OPENAI_API_KEY is set) -- asks the model
   to rate 0-100 fit against the student's profile and return a short
   summary plus matched skills.
2. Fallback keyword scoring (used when there's no API key, or if the API
   call fails for any reason) -- counts overlap between the job text and a
   fixed list of relevant keywords.

app.py should only ever call `rank_job()`; it picks the right path and
always returns a plain dict, so callers never have to deal with the
OpenAI client directly.
"""

import json
import re

from src.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    USER_PROFILE,
    FALLBACK_SKILL_KEYWORDS,
    PREFERRED_LOCATION_KEYWORDS,
)

_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI

        _client = OpenAI(api_key=OPENAI_API_KEY)
    except ImportError:
        _client = None


def _keyword_present(keyword: str, text: str) -> bool:
    """
    True if `keyword` appears in `text` as a whole word/phrase, not as a
    substring of some longer word. Plain `keyword in text` matching has a
    real bug here: "java" is a substring of "javascript", and "ai" is a
    substring of ordinary words like "maintain", "domain", and "training",
    so a posting with none of those skills would still rack up false
    keyword hits and an inflated score. Bounding the match on both sides by
    "not an alphanumeric character" (rather than regex \\b, which doesn't
    play well with symbol-containing keywords like "c++" or "c#") fixes
    both cases while still matching multi-word phrases like "machine
    learning" correctly.
    """
    pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _location_is_preferred(location: str) -> bool:
    loc = (location or "").lower()
    return any(marker in loc for marker in PREFERRED_LOCATION_KEYWORDS)


def _fallback_score(job: dict) -> dict:
    """Keyword-overlap scoring used when OpenAI isn't available."""
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()

    matched = [kw for kw in FALLBACK_SKILL_KEYWORDS if _keyword_present(kw, text)]

    # Simple, transparent formula: each matched keyword is worth a few
    # points, capped at 100 before the location bonus below. Gives a
    # reasonable spread without an API key.
    base_score = min(100, len(matched) * 12)

    # Small bonus for postings in a location the student actually said they
    # prefer (Northern VA/DC metro, NYC, or remote) -- two otherwise-tied
    # postings shouldn't score identically if one is a much better logistical
    # fit. Capped so it can push a good-but-not-maxed score up, never used to
    # manufacture a high score out of a skill-less posting.
    location_bonus = 8 if _location_is_preferred(job.get("location", "")) else 0
    score = min(100, base_score + location_bonus)

    if matched:
        summary = "Fallback keyword match on: " + ", ".join(matched[:6]) + "."
    else:
        summary = "No strong keyword overlap found with your profile."
    if location_bonus:
        summary += " Location matches your stated preference."

    return {"score": score, "summary": summary, "matched_skills": matched}


def _safe_parse_json(raw_text: str) -> dict:
    """Try to parse the model's response as JSON. Models sometimes wrap
    JSON in markdown code fences or add stray text, so this strips common
    wrappers before giving up."""
    text = raw_text.strip()

    if text.startswith("```"):
        text = text.strip("`")
        # drop a leading "json" language hint if present
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return {}


def _openai_score(job: dict) -> dict:
    """Ask OpenAI to score the job. Falls back to keyword scoring if the
    call fails or the response can't be parsed."""
    prompt = f"""
You are helping a college student evaluate internship postings.

Student profile:
{USER_PROFILE}

Internship posting:
Title: {job.get('title', '')}
Company: {job.get('company', '')}
Location: {job.get('location', '')}
Description: {job.get('description', '')}

Score this posting from 0 to 100 on how well it fits the student's profile
and goals. Respond with ONLY valid JSON in exactly this shape, no extra
commentary:

{{
  "score": <integer 0-100>,
  "summary": "<one or two sentence explanation>",
  "matched_skills": ["<skill1>", "<skill2>"]
}}
""".strip()

    try:
        response = _client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw_text = response.choices[0].message.content or ""
        parsed = _safe_parse_json(raw_text)

        score = parsed.get("score")
        summary = parsed.get("summary")
        matched_skills = parsed.get("matched_skills")

        if not isinstance(score, (int, float)) or not summary:
            # Response didn't have the shape we need -- fall back.
            return _fallback_score(job)

        return {
            "score": int(max(0, min(100, score))),
            "summary": str(summary),
            "matched_skills": matched_skills if isinstance(matched_skills, list) else [],
        }
    except Exception:
        # Any API/network error -- degrade gracefully rather than crash.
        return _fallback_score(job)


def rank_job(job: dict) -> dict:
    """Score a single job dict. Returns {"score", "summary", "matched_skills"}."""
    if _client is not None:
        return _openai_score(job)
    return _fallback_score(job)
