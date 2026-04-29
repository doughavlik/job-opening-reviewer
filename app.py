"""Flask app: job-opening-reviewer.

Serves a single-page UI at http://localhost:5000 with two tabs:
  * Job Openings — list of URLs, Add / Edit / Delete / Run Now
  * Settings — Gemini API key

On "Run Now" for a row, the app fetches the URL, asks Gemini to convert the
page to markdown, saves the markdown, and then asks Gemini to extract required
industry experience plus the supporting excerpt.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Flask, g, jsonify, render_template, request

try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:  # pragma: no cover - surfaced at runtime
    genai = None
    genai_types = None

try:
    import anthropic
except ImportError:  # pragma: no cover - surfaced at runtime
    anthropic = None

APP_ROOT = Path(__file__).parent
DB_PATH = APP_ROOT / "job_reviewer.db"
MODEL_NAME = "gemini-2.5-flash-lite"
ANTHROPIC_MODEL = "claude-sonnet-4-6"
ANTHROPIC_MAX_TOKENS = 2048
ANTHROPIC_MAX_WEB_SEARCHES = 5
SECRET_PLACEHOLDER = "********"

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_exc: BaseException | None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS job_openings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                markdown TEXT,
                industry_experience TEXT,
                industry_excerpt TEXT,
                status TEXT DEFAULT 'pending',
                error TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        existing_cols = {
            r[1] for r in conn.execute("PRAGMA table_info(job_openings)").fetchall()
        }
        for col in (
            "recruiter_name",
            "recruiter_title",
            "recruiter_linkedin",
            "recruiter_email",
            "alternate_recruiters",
        ):
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE job_openings ADD COLUMN {col} TEXT")
        conn.commit()


def get_setting(key: str) -> str | None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else None


def set_setting(key: str, value: str) -> None:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()


def get_gemini_api_key() -> str | None:
    """Settings DB takes precedence; fall back to GEMINI_API_KEY env var."""
    return get_setting("gemini_api_key") or os.environ.get("GEMINI_API_KEY")


def get_anthropic_api_key() -> str | None:
    """Settings DB takes precedence; fall back to ANTHROPIC_API_KEY env var."""
    return get_setting("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------

MARKDOWN_PROMPT = """\
You are converting a raw HTML job description into clean Markdown.

Return ONLY the Markdown content (no commentary, no code fences around the whole
document). Preserve headings, bullets, and paragraph structure. Strip navigation,
cookie banners, footer, and site chrome. Keep the actual job description text,
including company, title, responsibilities, requirements, benefits.

Raw HTML:
---
{html}
---
"""

EXTRACT_PROMPT = """\
Read the job description below and return ONLY a JSON object with these keys:

  - "industries": "none" OR a lowercase, comma+space-separated list of
    industries the candidate is required or strongly preferred to have prior
    experience in (e.g., "compliance, risk, legal, governance, financial
    services, healthcare IT, cybersecurity, legal tech").
  - "industry_excerpt": a short verbatim excerpt from the job description
    justifying the "industries" value. Empty string when "industries" is "none".
  - "primary_recruiter": a {{"name": "...", "title": "...", "linkedin": "...", "email": "..."}}
    object identifying the single most likely recruiter for this role. Apply
    these steps in order:
      1. If the job description names a recruiter, talent acquisition partner,
         or hiring contact, use that person.
      2. Otherwise, search LinkedIn for this company's recruiting team and
         pick the recruiter whose focus area (role function and geography)
         best matches this specific job description.
      3. Otherwise, search the company's own website — especially its About
         Us, Our Team, Leadership, or Careers pages (often fruitful for
         smaller companies) — for a named recruiter or people-team member.
    Take the role's function (engineering / sales / GTM / design / etc.) and
    geography into account when choosing.
    Rules for each field:
      - "name": the real person's name. LEAVE BLANK if you do not actually
        know a specific person — do not invent or guess a name.
      - "title": the person's current job title at this company if you know
        it (e.g., "Senior Technical Recruiter, EMEA"), typically from their
        LinkedIn profile or the company's Our Team page. Blank if unknown.
      - "linkedin": the person's actual LinkedIn URL
        (https://www.linkedin.com/in/<slug>) if you know it. LEAVE BLANK
        rather than fabricating a slug.
      - "email": the person's work email if you know it (often listed on
        company team pages). Blank if unknown.
  - "alternate_recruiters": a list of up to 3 other plausible recruiters for
    this role, each using the same object schema and the same no-fabrication
    rules. If fewer than 3 are actually known, return fewer — do not pad.

Return ONLY the JSON object, no commentary.

Job Description (Markdown):
---
{markdown}
---
"""


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json|markdown)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _gemini_client() -> "genai.Client":
    if genai is None:
        raise RuntimeError(
            "google-genai package is not installed. Run: pip install google-genai"
        )
    key = get_gemini_api_key()
    if not key:
        raise RuntimeError(
            "No Gemini API key configured. Set it in the Settings tab."
        )
    return genai.Client(api_key=key)


def _anthropic_client() -> "anthropic.Anthropic":
    if anthropic is None:
        raise RuntimeError(
            "anthropic package is not installed. Run: pip install anthropic"
        )
    key = get_anthropic_api_key()
    if not key:
        raise RuntimeError(
            "No Anthropic API key configured. Set it in the Settings tab."
        )
    return anthropic.Anthropic(api_key=key)


def _anthropic_generate_with_web_search(prompt: str, max_retries: int = 4) -> str:
    """Call Claude with the server-side web_search tool and return final text."""
    client = _anthropic_client()
    delay = 15
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=ANTHROPIC_MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
                tools=[
                    {
                        "type": "web_search_20250305",
                        "name": "web_search",
                        "max_uses": ANTHROPIC_MAX_WEB_SEARCHES,
                    }
                ],
            )
            parts = []
            for block in response.content:
                if getattr(block, "type", None) == "text":
                    parts.append(block.text)
            return "".join(parts)
        except Exception as exc:
            msg = str(exc)
            transient = (
                "429" in msg
                or "529" in msg
                or "overloaded" in msg.lower()
                or "rate_limit" in msg.lower()
            )
            if transient and attempt < max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise


_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)


def _requests_fetch_html(url: str) -> str:
    headers = {
        "User-Agent": _BROWSER_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _playwright_fetch_html(url: str) -> str:
    """Render the page in headless Chromium and return the post-JS HTML."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "playwright is required for the JS-render fallback. Run: "
            "pip install playwright && playwright install chromium"
        ) from exc

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(user_agent=_BROWSER_USER_AGENT)
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30_000)
            return page.content()
        finally:
            browser.close()


_APPONE_PATH_RE = re.compile(r"^/job/([0-9a-f]{16,})/?$", re.IGNORECASE)


def _is_appone_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.lower() == "apply.appone.com" and bool(
        _APPONE_PATH_RE.match(parsed.path or "")
    )


def _appone_adapter(url: str) -> tuple[str, str]:
    """Call AppOne's JSON job-posting API and synthesize markdown.

    AppOne is a SPA whose deep paths return HTTP 404 with a content-free shell;
    the real data lives at /api/apply/v2/jobposting/<id>. Falling through (by
    raising) lets fetch_content try the Playwright fallback.
    """
    parsed = urlparse(url)
    match = _APPONE_PATH_RE.match(parsed.path or "")
    if not match:
        raise ValueError(f"Not an AppOne job URL: {url}")
    job_id = match.group(1)
    api_url = f"https://apply.appone.com/api/apply/v2/jobposting/{job_id}"
    resp = requests.get(
        api_url,
        headers={
            "User-Agent": _BROWSER_USER_AGENT,
            "Accept": "application/json",
            "Referer": url,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    title = (data.get("jobTitle") or "").strip() or "Job Posting"
    location = (data.get("location") or "").strip()
    job_type = (data.get("jobType") or "").strip()
    description = (data.get("description") or "").strip()

    parts = [f"# {title}", ""]
    if location:
        parts.append(f"**Location:** {location}")
    if job_type:
        parts.append(f"**Type:** {job_type}")
    if location or job_type:
        parts.append("")
    parts.append(description)
    return ("markdown", "\n".join(parts).strip() + "\n")


# Registry of (predicate, adapter) pairs. Adapters return (kind, content)
# where kind is "markdown" (skip Gemini's HTML->markdown step) or "html".
ADAPTERS: list[tuple] = [
    (_is_appone_url, _appone_adapter),
]


def fetch_content(url: str) -> tuple[str, str]:
    """Fetch a job posting, returning (kind, content).

    Tries per-host adapters first, then a plain HTTP GET, and finally a
    headless-browser render so JS-only sites still work.
    """
    for matches, adapter in ADAPTERS:
        if matches(url):
            try:
                return adapter(url)
            except Exception:
                break  # fall through to generic path
    try:
        return ("html", _requests_fetch_html(url))
    except (requests.HTTPError, requests.RequestException):
        return ("html", _playwright_fetch_html(url))


def _gemini_generate(
    prompt: str,
    max_retries: int = 4,
    google_search: bool = False,
) -> str:
    """Call Gemini with exponential backoff on 429 / transient errors.

    When google_search=True, enables the Google Search grounding tool so
    the model can consult live sources (e.g., LinkedIn, company team pages).
    """
    client = _gemini_client()
    config = None
    if google_search and genai_types is not None:
        config = genai_types.GenerateContentConfig(
            tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())]
        )
    delay = 15  # seconds before first retry
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config=config,
            )
            return response.text or ""
        except Exception as exc:
            msg = str(exc)
            is_transient = (
                "429" in msg
                or "RESOURCE_EXHAUSTED" in msg
                or "503" in msg
                or "UNAVAILABLE" in msg
                or "500" in msg
                or "INTERNAL" in msg
            )
            if is_transient and attempt < max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise


_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript|svg|template)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_TAG_CHROME_RE = re.compile(
    r"<(nav|footer|header|aside)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)


def _strip_html_chrome(html: str) -> str:
    """Remove scripts/styles/nav/footer/comments to shrink input sent to Gemini."""
    html = _COMMENT_RE.sub("", html)
    html = _SCRIPT_STYLE_RE.sub("", html)
    html = _TAG_CHROME_RE.sub("", html)
    return html


def html_to_markdown(html: str) -> str:
    cleaned = _strip_html_chrome(html)
    snippet = cleaned[:80_000]
    return _strip_code_fences(_gemini_generate(MARKDOWN_PROMPT.format(html=snippet)))


def _clean_recruiter(obj) -> dict:
    if not isinstance(obj, dict):
        return {"name": "", "title": "", "linkedin": "", "email": ""}
    return {
        "name": str(obj.get("name", "")).strip(),
        "title": str(obj.get("title", "")).strip(),
        "linkedin": str(obj.get("linkedin", "")).strip(),
        "email": str(obj.get("email", "")).strip(),
    }


def extract_fields(markdown: str) -> dict:
    """Single Claude call with web_search tool:
    industries + recruiter primary/alternates (name, title, linkedin, email).
    Falls back to Gemini if no Anthropic key is configured.
    """
    prompt = EXTRACT_PROMPT.format(markdown=markdown[:30_000])
    if get_anthropic_api_key():
        raw = _anthropic_generate_with_web_search(prompt)
    else:
        raw = _gemini_generate(prompt, google_search=True)
    text = _strip_code_fences(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            data = {}
        else:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                data = {}

    industries = str(data.get("industries", "none")).strip() or "none"
    excerpt = str(data.get("industry_excerpt", "")).strip()

    primary = _clean_recruiter(data.get("primary_recruiter"))

    alternates_raw = data.get("alternate_recruiters") or []
    alternates = []
    if isinstance(alternates_raw, list):
        for item in alternates_raw:
            cleaned = _clean_recruiter(item)
            if any(cleaned.values()):
                alternates.append(cleaned)

    # Promote the first alternate to primary when primary is blank.
    if not primary["name"] and alternates:
        primary = alternates.pop(0)

    return {
        "industries": industries,
        "excerpt": excerpt,
        "recruiter_name": primary["name"],
        "recruiter_title": primary["title"],
        "recruiter_linkedin": primary["linkedin"],
        "recruiter_email": primary["email"],
        "alternate_recruiters": json.dumps(alternates),
    }


def process_opening(opening_id: int) -> None:
    """Fetch URL -> markdown via Gemini -> industry extraction via Gemini."""
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        row = db.execute(
            "SELECT id, url FROM job_openings WHERE id=?", (opening_id,)
        ).fetchone()
        if row is None:
            return
        url = row["url"]
        db.execute(
            "UPDATE job_openings SET status='running', error=NULL WHERE id=?",
            (opening_id,),
        )
        db.commit()

        kind, content = fetch_content(url)
        markdown = content if kind == "markdown" else html_to_markdown(content)
        fields = extract_fields(markdown)

        db.execute(
            """
            UPDATE job_openings
               SET markdown=?, industry_experience=?, industry_excerpt=?,
                   recruiter_name=?, recruiter_title=?,
                   recruiter_linkedin=?, recruiter_email=?,
                   alternate_recruiters=?,
                   status='done', error=NULL,
                   updated_at=datetime('now')
             WHERE id=?
            """,
            (markdown, fields["industries"], fields["excerpt"],
             fields["recruiter_name"], fields["recruiter_title"],
             fields["recruiter_linkedin"], fields["recruiter_email"],
             fields["alternate_recruiters"],
             opening_id),
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.execute(
            """
            UPDATE job_openings
               SET status='error', error=?, updated_at=datetime('now')
             WHERE id=?
            """,
            (str(exc), opening_id),
        )
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.get("/api/openings")
def list_openings():
    rows = get_db().execute(
        "SELECT id, url, markdown, industry_experience, industry_excerpt, "
        "recruiter_name, recruiter_title, recruiter_linkedin, recruiter_email, "
        "alternate_recruiters, "
        "status, error, updated_at FROM job_openings ORDER BY id DESC"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/api/openings/<int:opening_id>")
def get_opening(opening_id: int):
    row = get_db().execute(
        "SELECT * FROM job_openings WHERE id=?", (opening_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    return jsonify(dict(row))


@app.post("/api/openings")
def add_opening():
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400
    db = get_db()
    cur = db.execute(
        "INSERT INTO job_openings(url, status, updated_at) "
        "VALUES(?, 'pending', datetime('now'))",
        (url,),
    )
    db.commit()
    return jsonify({"id": cur.lastrowid}), 201


@app.put("/api/openings/<int:opening_id>")
def update_opening(opening_id: int):
    data = request.get_json(force=True, silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "url is required"}), 400
    db = get_db()
    db.execute(
        "UPDATE job_openings SET url=?, updated_at=datetime('now') WHERE id=?",
        (url, opening_id),
    )
    db.commit()
    return jsonify({"ok": True})


@app.delete("/api/openings/<int:opening_id>")
def delete_opening(opening_id: int):
    db = get_db()
    db.execute("DELETE FROM job_openings WHERE id=?", (opening_id,))
    db.commit()
    return jsonify({"ok": True})


@app.post("/api/openings/<int:opening_id>/run")
def run_opening(opening_id: int):
    db = get_db()
    row = db.execute(
        "SELECT id FROM job_openings WHERE id=?", (opening_id,)
    ).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    db.execute(
        "UPDATE job_openings SET status='queued', error=NULL WHERE id=?",
        (opening_id,),
    )
    db.commit()
    threading.Thread(target=process_opening, args=(opening_id,), daemon=True).start()
    return jsonify({"ok": True, "status": "queued"})


@app.get("/api/settings")
def get_settings():
    # Never return the raw key; expose only a 7-char prefix for visual confirmation.
    gem = get_gemini_api_key()
    ant = get_anthropic_api_key()
    return jsonify(
        {
            "gemini_api_key_set": bool(gem),
            "gemini_api_key_prefix": (gem[:7] if gem else ""),
            "anthropic_api_key_set": bool(ant),
            "anthropic_api_key_prefix": (ant[:7] if ant else ""),
        }
    )


@app.put("/api/settings")
def update_settings():
    data = request.get_json(force=True, silent=True) or {}
    gem = (data.get("gemini_api_key") or "").strip()
    if gem and gem != SECRET_PLACEHOLDER:
        set_setting("gemini_api_key", gem)
    ant = (data.get("anthropic_api_key") or "").strip()
    if ant and ant != SECRET_PLACEHOLDER:
        set_setting("anthropic_api_key", ant)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
