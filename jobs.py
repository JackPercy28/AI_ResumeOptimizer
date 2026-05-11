"""
jobs.py — Fetches real Malaysian job listings from JSearch API (via RapidAPI).

Setup:
  1. Go to https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
  2. Sign up free → Subscribe to Basic (free tier: 200 requests/month)
  3. Copy your API key
  4. Add to your .env file:  JSEARCH_API_KEY=your_key_here
"""

import os
import requests
from difflib import SequenceMatcher


JSEARCH_URL = "https://jsearch.p.rapidapi.com/search"


def _similarity(a: str, b: str) -> float:
    """Simple string similarity ratio between 0 and 1."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _score_job(job: dict, keywords_found: list[str], job_title_query: str) -> int:
    """
    Score a real job listing against the user's resume profile.
    Returns an integer match percentage (0–100).
    """
    score = 0

    # 1. Title similarity (up to 40 pts)
    real_title = job.get("job_title", "")
    title_sim = _similarity(real_title, job_title_query)
    score += int(title_sim * 40)

    # 2. Keyword overlap in job description (up to 45 pts)
    description = (job.get("job_description") or "").lower()
    if description and keywords_found:
        matched = sum(1 for kw in keywords_found if kw.lower() in description)
        keyword_ratio = matched / len(keywords_found)
        score += int(keyword_ratio * 45)

    # 3. Has salary info bonus (up to 5 pts)
    if job.get("job_min_salary") or job.get("job_max_salary"):
        score += 5

    # 4. Job type match — full-time preferred (up to 10 pts)
    if job.get("job_employment_type", "").upper() == "FULLTIME":
        score += 10

    return min(score, 99)  # cap at 99 — 100 reserved for perfect


def fetch_malaysia_jobs(job_titles: list[str], keywords_found: list[str],max_results: int = 6,) -> list[dict]:
    JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")  # ← add this
    HEADERS = {                                           # ← add this
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
    }   
    """
    Fetch real job listings from Malaysia using JSearch API.

    Args:
        job_titles:      List of job titles extracted from resume analysis
                         e.g. ["Software Engineer", "Full Stack Developer"]
        keywords_found:  Keywords from resume to score relevance
        max_results:     How many jobs to return in the dashboard

    Returns:
        List of job dicts formatted for dashboard rendering:
        [
          {
            "title": str,
            "company": str,
            "location": str,
            "match_pct": int,
            "apply_link": str,
            "salary": str,          # e.g. "MYR 5,000 – 8,000/mo" or ""
            "job_type": str,        # e.g. "Full-time"
            "posted": str,          # e.g. "2 days ago"
          },
          ...
        ]
    """

    all_jobs = []
    seen_ids = set()

    # Query each job title — take top 3 results per title
    for title in job_titles[:3]:  # max 3 title queries to save API calls
        query = f"{title} in Malaysia"
        params = {
            "query": query,
            "page": "1",
            "num_pages": "1",
            "country": "my",
            "date_posted": "month",   # jobs from last 30 days
        }

        try:
            resp = requests.get(
                JSEARCH_URL,
                headers=HEADERS,
                params=params,
                timeout=8,
            )
            resp.raise_for_status()
            data = resp.json()
            jobs_raw = data.get("data", [])

            for job in jobs_raw[:4]:  # top 4 per query
                job_id = job.get("job_id", "")
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                # Build salary string
                salary = ""
                min_s = job.get("job_min_salary")
                max_s = job.get("job_max_salary")
                currency = job.get("job_salary_currency", "MYR")
                period = job.get("job_salary_period", "")
                period_map = {
                    "MONTH": "/mo", "YEAR": "/yr",
                    "HOUR": "/hr", "WEEK": "/wk",
                }
                period_label = period_map.get(period, "")
                if min_s and max_s:
                    salary = f"{currency} {int(min_s):,} – {int(max_s):,}{period_label}"
                elif min_s:
                    salary = f"{currency} {int(min_s):,}+{period_label}"

                # Build posted-ago string
                posted_ts = job.get("job_posted_at_timestamp")
                posted = ""
                if posted_ts:
                    import time
                    days_ago = int((time.time() - posted_ts) / 86400)
                    if days_ago == 0:
                        posted = "Today"
                    elif days_ago == 1:
                        posted = "Yesterday"
                    elif days_ago < 30:
                        posted = f"{days_ago}d ago"
                    else:
                        posted = "30d+ ago"

                # City / state
                city = job.get("job_city") or ""
                state = job.get("job_state") or ""
                location_parts = [p for p in [city, state, "Malaysia"] if p]
                location = ", ".join(location_parts[:2]) or "Malaysia"

                match_pct = _score_job(job, keywords_found, title)

                all_jobs.append({
                    "title": job.get("job_title", title),
                    "company": job.get("employer_name", "—"),
                    "location": location,
                    "match_pct": match_pct,
                    "apply_link": job.get("job_apply_link", ""),
                    "salary": salary,
                    "job_type": _fmt_employment_type(job.get("job_employment_type", "")),
                    "posted": posted,
                })

        except requests.exceptions.Timeout:
            # API timed out — continue with what we have
            continue
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                # Rate limited — stop querying
                break
            continue
        except Exception:
            continue

    if not all_jobs:
        return _fallback_jobs()

    # Sort by match score descending, dedupe companies, return top N
    all_jobs.sort(key=lambda j: j["match_pct"], reverse=True)

    seen_companies = set()
    unique_jobs = []
    for job in all_jobs:
        co = job["company"].lower()
        if co not in seen_companies:
            seen_companies.add(co)
            unique_jobs.append(job)
        if len(unique_jobs) >= max_results:
            break

    return unique_jobs


def _fmt_employment_type(raw: str) -> str:
    mapping = {
        "FULLTIME": "Full-time",
        "PARTTIME": "Part-time",
        "CONTRACTOR": "Contract",
        "INTERN": "Internship",
    }
    return mapping.get(raw.upper(), raw.title()) if raw else "Full-time"


def _fallback_jobs() -> list[dict]:
    """
    Returned when API key is missing or all requests fail.
    These are placeholder entries that tell the user to configure the API.
    """
    return [
        {
            "title": "Add your JSearch API key",
            "company": "See .env setup instructions",
            "location": "Malaysia",
            "match_pct": 0,
            "apply_link": "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch",
            "salary": "",
            "job_type": "",
            "posted": "",
        }
    ]