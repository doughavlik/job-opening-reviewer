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

import requests
from flask import Flask, g, jsonify, render_template, request

try:
    from google import genai
except ImportError:  # pragma: no cover - surfaced at runtime
    genai = None

APP_ROOT = Path(__file__).parent
DB_PATH = APP_ROOT / "job_reviewer.db"
MODEL_NAME = "gemini-2.0-flash"
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

INDUSTRY_PROMPT = """\
You are extracting required industry experience from a job description.

Read the job description below and determine which industries (if any) the
candidate is required, or strongly preferred, to have prior experience in.

Return ONLY a JSON object with exactly these two keys:
  - "industries": either the string "none" OR a comma-delimited string listing
    the required industries (e.g., "compliance, risk, legal, governance,
    financial services, healthcare IT, cybersecurity, legal tech"). Use
    lowercase, comma+space separated.
  - "excerpt": a short verbatim excerpt from the job description that justifies
    your answer. If "industries" is "none", set this to an empty string.

Example:
{{"industries": "compliance, risk, legal, governance, financial services, healthcare IT, cybersecurity, legal tech", "excerpt": "Experience serving compliance, risk, legal, or governance buyers in financial services \u2014 or a strong track record in adjacent trust-sensitive environments (healthcare IT, cybersecurity, legal tech)"}}

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


def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _gemini_generate(prompt: str, max_retries: int = 4) -> str:
    """Call Gemini with exponential backoff on 429 / transient errors."""
    client = _gemini_client()
    delay = 15  # seconds before first retry
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
            return response.text or ""
        except Exception as exc:
            is_rate_limit = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
            if is_rate_limit and attempt < max_retries:
                time.sleep(delay)
                delay *= 2
                continue
            raise


def html_to_markdown(html: str) -> str:
    snippet = html[:200_000]
    return _strip_code_fences(_gemini_generate(MARKDOWN_PROMPT.format(html=snippet)))


def extract_industry(markdown: str) -> tuple[str, str]:
    text = _strip_code_fences(
        _gemini_generate(INDUSTRY_PROMPT.format(markdown=markdown[:30_000]))
    )
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Attempt to recover the first {...} block.
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))
    industries = str(data.get("industries", "none")).strip() or "none"
    excerpt = str(data.get("excerpt", "")).strip()
    return industries, excerpt


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

        html = fetch_html(url)
        markdown = html_to_markdown(html)
        industries, excerpt = extract_industry(markdown)

        db.execute(
            """
            UPDATE job_openings
               SET markdown=?, industry_experience=?, industry_excerpt=?,
                   status='done', error=NULL,
                   updated_at=datetime('now')
             WHERE id=?
            """,
            (markdown, industries, excerpt, opening_id),
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
        "SELECT id, url, markdown, industry_experience, industry_excerpt, status, error, "
        "updated_at FROM job_openings ORDER BY id DESC"
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
    # Never return the raw key; indicate presence only.
    has_key = bool(get_gemini_api_key())
    return jsonify({"gemini_api_key_set": has_key})


@app.put("/api/settings")
def update_settings():
    data = request.get_json(force=True, silent=True) or {}
    key = (data.get("gemini_api_key") or "").strip()
    if key and key != SECRET_PLACEHOLDER:
        set_setting("gemini_api_key", key)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> None:
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
