# job-opening-reviewer

Single-page Flask web app for monitoring job openings. Given a URL to a job description, it:

1. Fetches the page and uses Google Gemini (`gemini-2.0-flash`) to convert it to markdown
2. Stores the markdown in a local SQLite database
3. Uses Gemini to extract structured fields from the markdown (e.g. required Industry Experience)

## Requirements

- Python 3.10+
- A Google Gemini API key (set in the **Settings** tab, or as the `GEMINI_API_KEY` environment variable)

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open <http://localhost:5000>.

## Tabs

- **Job Openings** — table of URLs; add, edit, delete, run extraction
- **Settings** — enter your Gemini API key (stored in SQLite, masked on the UI)

## Data

A local SQLite file `job_reviewer.db` is created on first run with two tables: `job_openings` and `settings`.
