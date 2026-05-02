# Job Opening Reviewer — Main Table Column Spec

> **Purpose.** Authoritative, column-by-column description of the main table on the **Job Openings** tab. Used as the working spec when proposing or implementing new columns. Companion to [`UI Design Spec — As-Is.md`](UI%20Design%20Spec%20%E2%80%94%20As-Is.md) (full UI snapshot) and [`Job Opening Reviewer — UI Review - 2026-04-30 1117 Claude Code.md`](Job%20Opening%20Reviewer%20%E2%80%94%20UI%20Review%20-%202026-04-30%201117%20Claude%20Code.md) (critique).
>
> **Source of truth.** Column rendering: [`templates/index.html`](templates/index.html). Backend / DB / AI: [`app.py`](app.py).

---

## 1. Column inventory (left → right)

| # | Header | DB column(s) | Origin | Editable in UI | Sortable | Hideable |
|---|---|---|---|---|---|---|
| 1 | **#** | `id` | System (autoincrement) | No | Yes | Yes |
| 2 | **Job Opening URL** | `url` | User entry | Yes (inline edit) | Yes | Yes |
| 3 | **Industry Experience** | `industry_experience` | AI (Claude/Gemini extraction) | No | Yes | Yes |
| 4 | **Excerpt** | `industry_excerpt` | AI (Claude/Gemini extraction) | No | No | Yes |
| 5 | **Recruiter** | `recruiter_name`, `recruiter_title`, `recruiter_linkedin`, `recruiter_email`, `alternate_recruiters` | AI (Claude/Gemini extraction + web search) | No | Yes (by `recruiter_name`) | Yes |
| 6 | **Status** | `status`, `error` | System (state machine) | No | Yes | Yes |
| 7 | **Job Description** | `markdown` | AI (Gemini HTML→Markdown), or per-host adapter | No | No | Yes |
| 8 | **Actions** | — | UI controls | n/a | No | No |

Column visibility, order, sort direction, and width are all persisted per-browser in `localStorage` (keys: `jobReviewer_colVis`, `jobReviewer_colWidths`, `jobReviewer_sortCol`, `jobReviewer_sortAsc`). The frontend column registry lives at [`templates/index.html:182`](templates/index.html#L182) (`COLUMNS` array).

---

## 2. Column-by-column detail

### 2.1 `#` — Row ID

- **Header:** `#`
- **Data shown:** integer row id (`id` column).
- **Purpose:** Stable identifier for each saved opening. Doubles as the natural insertion-order indicator.
- **Behavior:** Read-only. Assigned by SQLite (`INTEGER PRIMARY KEY AUTOINCREMENT`) on row insert ([`app.py:73`](app.py#L73)).
- **Sort:** Default sort. Descending by default (`sortAsc=false`) so newest rows appear at top ([`templates/index.html:202`](templates/index.html#L202)).
- **Default width:** 50 px.

### 2.2 `Job Opening URL`

- **Header:** `Job Opening URL`
- **Data shown:** Full URL, rendered as a truncated external `<a>` link (`target="_blank"`). Tooltip shows the full URL.
- **Purpose:** Identifies the job posting. The only required field when adding a row.
- **Behavior:** **User-edited.** Set on Add (`POST /api/openings`) and changed via the per-row Edit action (`PUT /api/openings/<id>`). Validation is minimal — the backend rejects only an empty string ([`app.py:592`](app.py#L592)).
- **Sort:** Lexicographic, by `url`.
- **Default width:** 220 px.
- **Notes for redesign:** Editing replaces the cell with an `<input>` and swaps the action buttons for Save/Cancel — the row enters an "edit mode" that affects two columns simultaneously. Any column-level redesign that modifies the Actions cell must keep this in mind.

### 2.3 `Industry Experience`

- **Header:** `Industry Experience`
- **Data shown:** Plain text — either `none` or a lowercase, comma-separated list of industries the candidate is required or strongly preferred to have experience in (e.g., `compliance, risk, legal, governance`).
- **Purpose:** Lets the user quickly judge whether the role requires industry experience they have or lack. The single most decision-relevant signal in the table.
- **Behavior:** **AI-populated.** Filled by `extract_fields()` ([`app.py:457`](app.py#L457)) when the row's "Run Now" pipeline completes successfully. Persists across runs; re-runs overwrite.
- **Sort:** Lexicographic, by `industry_experience`.
- **Default width:** 160 px.
- **Prompt (verbatim, from [`app.py:148`](app.py#L148) `EXTRACT_PROMPT`):**
  > `"industries"`: `"none"` OR a lowercase, comma+space-separated list of industries the candidate is required or strongly preferred to have prior experience in (e.g., `"compliance, risk, legal, governance, financial services, healthcare IT, cybersecurity, legal tech"`).
- **Model & tools:** Claude Sonnet 4.6 with Anthropic's `web_search_20250305` tool when an Anthropic key is configured; otherwise Gemini 2.5 Flash Lite with Google Search grounding ([`app.py:457`](app.py#L457)).
- **Quirks:** The literal string `none` (not empty) means "no specific industry required" — sort and any future filter UI must distinguish `none` from a missing/empty value (which means "not yet extracted").

### 2.4 `Excerpt`

- **Header:** `Excerpt`
- **Data shown:** Two-line clamped teaser of `industry_excerpt`, with a **View** button that opens the full text in a modal (`#markdownModal`).
- **Purpose:** Provides verbatim evidence backing the Industry Experience value, so the user can sanity-check the extraction without opening the source URL.
- **Behavior:** **AI-populated** in the same call as `industry_experience`. Empty when `industries == "none"`.
- **Sort:** Not sortable.
- **Default width:** 200 px.
- **Prompt (verbatim, from [`app.py:148`](app.py#L148) `EXTRACT_PROMPT`):**
  > `"industry_excerpt"`: a short verbatim excerpt from the job description justifying the `"industries"` value. Empty string when `"industries"` is `"none"`.
- **Notes for redesign:** Excerpt and Industry Experience are produced by the same JSON object in one API call, but are rendered as two independent columns. If a future column also derives from this same call, prefer extending `EXTRACT_PROMPT` over adding a second extraction round-trip.

### 2.5 `Recruiter`

- **Header:** `Recruiter`
- **Data shown:** Composite cell:
  - Primary recruiter name (or `(unnamed)` placeholder).
  - LinkedIn icon-link (if known).
  - `+N` badge counting alternate recruiters.
  - Whole cell click → opens `#recruiterModal` showing primary (name, title, LinkedIn, email) and up to 3 alternates.
- **Purpose:** Surface the most likely person to contact about the role, plus runner-ups if the primary turns out wrong.
- **Behavior:** **AI-populated** in the same `extract_fields()` call as Industry Experience and Excerpt. Five DB columns are written: `recruiter_name`, `recruiter_title`, `recruiter_linkedin`, `recruiter_email`, and `alternate_recruiters` (a JSON array of `{name, title, linkedin, email}` objects).
- **Sort:** By `recruiter_name` only — title, LinkedIn, email, and alternates do not participate.
- **Default width:** 200 px.
- **Prompt (verbatim, from [`app.py:148`](app.py#L148) `EXTRACT_PROMPT`):**
  > `"primary_recruiter"`: a `{"name": "...", "title": "...", "linkedin": "...", "email": "..."}` object identifying the single most likely recruiter for this role. Apply these steps in order:
  >   1. If the job description names a recruiter, talent acquisition partner, or hiring contact, use that person.
  >   2. Otherwise, search LinkedIn for this company's recruiting team and pick the recruiter whose focus area (role function and geography) best matches this specific job description.
  >   3. Otherwise, search the company's own website — especially its About Us, Our Team, Leadership, or Careers pages (often fruitful for smaller companies) — for a named recruiter or people-team member.
  >
  > Take the role's function (engineering / sales / GTM / design / etc.) and geography into account when choosing.
  > Rules for each field:
  >   - `"name"`: the real person's name. LEAVE BLANK if you do not actually know a specific person — do not invent or guess a name.
  >   - `"title"`: the person's current job title at this company if you know it (e.g., `"Senior Technical Recruiter, EMEA"`), typically from their LinkedIn profile or the company's Our Team page. Blank if unknown.
  >   - `"linkedin"`: the person's actual LinkedIn URL (`https://www.linkedin.com/in/<slug>`) if you know it. LEAVE BLANK rather than fabricating a slug.
  >   - `"email"`: the person's work email if you know it (often listed on company team pages). Blank if unknown.
  >
  > `"alternate_recruiters"`: a list of up to 3 other plausible recruiters for this role, each using the same object schema and the same no-fabrication rules. If fewer than 3 are actually known, return fewer — do not pad.
- **Post-processing:** If `primary_recruiter.name` is blank but at least one alternate exists, the first alternate is promoted to primary ([`app.py:494`](app.py#L494)).
- **Notes for redesign:** This is the only "composite" column in the table — multiple DB fields, a click-anywhere modal trigger, an embedded link, and a count badge. Treat it as the design pattern to imitate (or deliberately deviate from) when another column needs to expose richer data than fits in plain text.

### 2.6 `Status`

- **Header:** `Status`
- **Data shown:** One of `pending`, `queued`, `running`, `done`, `error`. Color-coded via `.status-*` CSS classes. On `error`, the `error` field is shown as a tooltip on hover.
- **Purpose:** Tells the user where each row sits in the extraction pipeline, and surfaces failures.
- **Behavior:** **System-managed.** State transitions:
  - `pending` — set on row insert ([`app.py:73`](app.py#L73), default).
  - `queued` — set when user clicks **Run Now** ([`app.py:638`](app.py#L638)).
  - `running` — set when the worker thread picks up the job ([`app.py:519`](app.py#L519)).
  - `done` — set on successful completion ([`app.py:529`](app.py#L529)).
  - `error` — set on any exception in `process_opening`; `error` column captures the exception string ([`app.py:547`](app.py#L547)).
- **Sort:** Lexicographic on `status`. Note this gives an arbitrary alphabetical order (`done, error, pending, queued, running`), not a pipeline order.
- **Default width:** 90 px.
- **Polling:** When at least one row is `queued` or `running`, the UI re-fetches `/api/openings` every 2 s ([`templates/index.html:620`](templates/index.html#L620)).

### 2.7 `Job Description`

- **Header:** `Job Description`
- **Data shown:** Two-line clamped teaser of the cleaned-up Markdown, with a **View** button that opens the full Markdown in `#markdownModal` (with a Copy button). Empty rows show an em-dash.
- **Purpose:** Lets the user read the full posting from inside the app without leaving for the source URL — useful when the page has since been taken down or paywalled.
- **Behavior:** **AI-populated** (or adapter-supplied). Pipeline:
  1. `fetch_content(url)` tries per-host adapters first (currently AppOne JSON API), then `requests.get`, then a Playwright headless render ([`app.py:361`](app.py#L361)).
  2. If the adapter already returned Markdown, it's used as-is.
  3. Otherwise the HTML is stripped of `<script>`/`<style>`/`<nav>`/etc., truncated to 80 KB, and sent to Gemini for HTML→Markdown conversion ([`app.py:440`](app.py#L440)).
- **Sort:** Not sortable (would be useless on free-form prose).
- **Default width:** 260 px.
- **Prompt (verbatim, from [`app.py:134`](app.py#L134) `MARKDOWN_PROMPT`):**
  > You are converting a raw HTML job description into clean Markdown.
  >
  > Return ONLY the Markdown content (no commentary, no code fences around the whole document). Preserve headings, bullets, and paragraph structure. Strip navigation, cookie banners, footer, and site chrome. Keep the actual job description text, including company, title, responsibilities, requirements, benefits.
- **Model:** Gemini 2.5 Flash Lite (`MODEL_NAME`, [`app.py:40`](app.py#L40)). The cheaper model is intentional — this step is just structural cleanup, not analysis.

### 2.8 `Actions`

- **Header:** `Actions`
- **Data shown:** Three buttons: **Run Now** (▶), **Edit** (✎), **Delete** (🗑).
- **Purpose:** Per-row controls — re-trigger the pipeline, change the URL, or remove the row.
- **Behavior:** UI controls only — not backed by any DB column.
  - **Run Now:** `POST /api/openings/<id>/run` → status flips to `queued`, a daemon thread runs `process_opening` ([`app.py:630`](app.py#L630)). Re-running an already-completed row overwrites prior extracted fields.
  - **Edit:** Replaces the URL cell with an input, replaces these buttons with Save/Cancel; Save → `PUT /api/openings/<id>`.
  - **Delete:** `DELETE /api/openings/<id>` after a `confirm()`.
- **Hideable:** No (the only non-hideable column).
- **Sort:** No.
- **Default width:** 280 px (largest of any column — sized for the three-button cluster + Edit-mode Save/Cancel).

---

## 3. State that lives outside any column

These exist in the DB but have no dedicated column header, so any new column proposal should know they're available without a schema change:

| Field | Currently surfaced as | Could surface as |
|---|---|---|
| `error` | tooltip on the Status cell when status is `error` | a separate "Error" column, or an inline detail below Status |
| `updated_at` | not surfaced anywhere | a "Last run" / "Updated" column (ISO timestamp from `datetime('now')`) |
| `recruiter_title`, `recruiter_email` | only inside the recruiter modal | could be promoted to the row if email becomes the primary contact mechanism |
| `alternate_recruiters` (JSON array) | `+N` badge + modal | could expand into a "Backup contact" column |

---

## 4. Design notes for adding new columns

### 4.1 Decide where the data comes from

There are exactly four origins available today. Pick one and own its consequences:

1. **User-entered.** Like `url`. Means: add an inline-edit affordance, validation, and a corresponding `PUT` field. Cheap and predictable.
2. **AI-extracted from the markdown** (no web search). Edit `EXTRACT_PROMPT`, add the field name to the JSON contract, parse it in `extract_fields()`, persist it, render it. Adds zero API round-trips because it piggybacks the existing single Claude/Gemini call.
3. **AI-extracted with web search.** Same as (2) but acknowledge that latency and cost grow with `ANTHROPIC_MAX_WEB_SEARCHES` (currently 5). Don't add multiple search-heavy fields without bumping that limit or splitting the call.
4. **System-derived.** Computed from existing DB state (e.g. age of `updated_at`, length of `markdown`, count of alternates). Free; no model involved.

**Strongly prefer (2) over a new round-trip.** Recruiter, Industry, and Excerpt are all in one JSON response today — adding "summary", "seniority", "comp band", etc., to the same prompt is far cheaper and faster than introducing a second LLM call.

### 4.2 Sort, filter, and the empty-vs-`none` trap

`industry_experience` already shows the trap: a populated value of `"none"` and a never-extracted empty string are *different states with different meanings* but sort/group together if treated as plain strings. For any new AI column, decide up front:

- What's the "AI knows this doesn't apply" sentinel? (`none`, empty list, `null`, `"unknown"`?)
- What's the "AI hasn't run yet" state? (typically empty / `NULL` in the DB)
- How should sort handle each? (Today: sort is naive lexicographic; both states sort together at the top.)

If the column will get a filter UI later, codify the sentinel as a constant in `app.py` rather than a magic string.

### 4.3 One column ≠ one DB field

Recruiter is the precedent: one column, five DB fields, an inline link, a count badge, and a modal. When adding a new column, ask whether it's:

- **Atomic** (single string/number, like Industry Experience) — easy.
- **Composite** (multiple structured fields displayed together, like Recruiter) — needs a render function, decide on sort key, decide which fields go in the cell vs a drill-down.
- **List-valued** (zero-to-many items, like alternates) — needs a count badge or chip group, and a deeper view.

Match the precedent for the closest existing column, or document a deliberate departure.

### 4.4 Rendering budget

The table is `table-layout: fixed` with manual column widths persisted per-user. Six of the eight columns are already > 150 px wide; the page already scrolls horizontally on narrower viewports. Before adding a column, decide:

- Can it sit at < 100 px? (good — `Status`-sized)
- Does it need 200+ px? (it counts against horizontal real estate — consider whether it earns its place or belongs in a row-detail view)
- Could two atomic columns be merged into one composite? (Industry + Excerpt is a candidate — both come from the same call and are read together.)

### 4.5 The "Run Now" reprocessing contract

Re-running a row overwrites every AI-populated field. Any new AI column inherits this — the user expects "Run Now" to refresh the column. Don't add an AI column whose value is expensive to recompute and silently sticks; if it must be sticky, add a separate "lock" or "manual override" flag and a UI to manage it.

### 4.6 Backward-compatible schema additions

`init_db()` ([`app.py:69`](app.py#L69)) already does the right thing — `CREATE TABLE IF NOT EXISTS` for greenfield, `ALTER TABLE ADD COLUMN` for known-but-missing columns. New columns should be added to the same loop so existing local databases auto-migrate on next launch.

### 4.7 Frontend wiring checklist (for any new column)

When promoting a new field to a column, you'll touch all of:

1. `init_db()` migration loop — [`app.py:89`](app.py#L89).
2. `EXTRACT_PROMPT` JSON contract — [`app.py:148`](app.py#L148) (if AI).
3. `extract_fields()` parsing + return dict — [`app.py:457`](app.py#L457).
4. `process_opening()` UPDATE statement — [`app.py:529`](app.py#L529).
5. `list_openings()` SELECT — [`app.py:570`](app.py#L570).
6. `<thead>` row in `index.html` — [`templates/index.html:86`](templates/index.html#L86).
7. `COLUMNS` array — [`templates/index.html:182`](templates/index.html#L182).
8. `buildRow()` — [`templates/index.html:317`](templates/index.html#L317).
9. (Optional) sort: only if `sortable: true` and a real `sortCol` is provided.

Skip any of these and the column will silently disappear, fail to sort, or fail to persist.

### 4.8 Settings & cost implications

If the new column requires a different model (e.g. Opus for harder reasoning), or a different tool (e.g. Gemini's URL context tool, or a longer web-search budget), surface that in the **Settings** tab so the user can see and control it. Don't bury per-column config in code constants forever.

---

## 5. Quick-add template

When proposing a new column, fill this in and append it to §2:

```
### 2.x `<Column Header>`

- **Header:** `<exact header text>`
- **Data shown:** <what the cell renders, including any teaser/badge/modal pattern>
- **Purpose:** <one sentence — what decision does this help the user make?>
- **Behavior:** <user-edited | AI-populated | system-derived>; <when it's set; what overwrites it>
- **DB column(s):** `<col_a>`, `<col_b>` (and types — TEXT/INTEGER/JSON-as-TEXT)
- **Sort:** <yes/no, and if yes which DB column>
- **Default width:** <px>
- **Prompt (if AI):** <verbatim text or "extends EXTRACT_PROMPT — add JSON key X with rules Y">
- **Model & tools:** <Claude | Gemini | both, with which tool>
- **Sentinel for "not applicable":** <e.g. "none", empty list, null>
- **Notes / quirks:** <anything future-you needs to remember>
```
