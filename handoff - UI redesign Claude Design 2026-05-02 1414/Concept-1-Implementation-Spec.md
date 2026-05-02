# Job Opening Reviewer — Concept 01 "Operations Console" Implementation Spec

> **Audience.** Claude Code (or any engineer) implementing the redesign in `templates/index.html`.
> **Scope.** Replace the current Bootstrap admin table with the Operations Console design. Backend API and DB schema are unchanged except for the new columns listed in §3.
> **Companion files** (already in repo):
> - `UI Design Spec — As-Is.md` — current UI baseline & constraints
> - `Main Table Columns — Spec.md` — column-level data contract
> - `app.py` — Flask backend (do not break the API surface)

---

## 1. Visual design system

### 1.1 Palette (warm neutral + single warm accent)

| Token            | Value         | Usage                                                     |
|------------------|---------------|-----------------------------------------------------------|
| `--bg-page`      | `#fbfaf7`     | Page background, frozen panel background                  |
| `--bg-toolbar`   | `#f5f2ec`     | Toolbar strip behind URL input + filters                  |
| `--bg-pane`      | `#f7f3ec`     | Reading pane background (slightly warmer than page)       |
| `--bg-card`      | `#ffffff`     | Excerpt card inside reading pane, action buttons          |
| `--ink`          | `#1a1a1a`     | Primary text, active tab background                       |
| `--ink-muted`    | `#3a3a3a`     | Filter chip text, secondary copy                          |
| `--text-soft`    | `#5a5246`     | Location text, body inside pane                           |
| `--text-meta`    | `#8b8676`     | Header labels, "v2.4 · local", row #s, updated timestamps |
| `--text-faint`   | `#a8a39a`     | Hints inside input ("Press Enter to run")                 |
| `--border`       | `#e8e4dc`     | Section dividers (header, stat strip, toolbar)            |
| `--border-row`   | `#efebe2`     | Row dividers in table                                     |
| `--border-pane`  | `#e6dfd2`     | Reading pane internal dividers                            |
| `--border-input` | `#e0dccf`     | Inputs, action buttons, pane buttons                      |
| `--accent`       | `#9a6a14`     | Selected-row stripe, "partial" / "running" semantic       |
| `--accent-bg`    | `rgba(154,106,20,0.06)` | Selected-row tint                               |

**Status colors** (foreground / background pair):
- `done`    → `#0d6e54` on `#e8efe8`
- `running` → `#9a6a14` on `#fff4e0`
- `error`   → `#9a3a2a` on `#fbe5e1`
- `queued`  → `#3a558a` on `#e6ecf5`
- `pending` → `#8b8676` on `#f5f2ec`

**Remote pill colors:**
- `Remote`     → `#0d6e54` on `#e8efe8`
- `Hybrid`     → `#3a558a` on `#e6ecf5`
- `In-office`  → `#7a6a4a` on `#f0ebe0`
- `Other`      → `#8b8676` on `#f5f2ec`
- `Unspecified`→ `#a8a39a` on `#f5f2ec`

**Match colors:**
- `strong`  → `#0d6e54` (filled `●`)
- `partial` → `#9a6a14` (half `◐`)
- `none`    → `#9a9893` (empty `○`)

### 1.2 Typography

Load from Google Fonts:
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600&display=swap" rel="stylesheet">
```

| Element                          | Family            | Size  | Weight | Notes                       |
|----------------------------------|-------------------|-------|--------|-----------------------------|
| Wordmark "Job Opening Reviewer"  | Source Serif 4   | 19px  | 600    | letter-spacing -0.01em      |
| Stat-strip numbers (142, 34, …)  | Source Serif 4   | 26px  | 600    | letter-spacing -0.02em      |
| Reading-pane H1 (job title)      | Source Serif 4   | 28px  | 600    | line-height 1.15            |
| Reading-pane prose (markdown)    | Source Serif 4   | 14px  | 400    | line-height 1.6             |
| Reading-pane excerpt italic      | Source Serif 4   | 13.5px| 400    | italic                      |
| Section labels (UPPERCASE)       | Inter            | 10px  | 400    | letter-spacing 0.10–0.12em  |
| Table headers                    | Inter            | 10px  | 400    | UPPERCASE, letter-spacing 0.10em |
| Cell body text                   | Inter            | 12–13px | 400/500 | tabular-nums on numbers   |
| Status / remote pills            | Inter            | 10.5–11px | 500 |                              |

### 1.3 Spacing & rhythm

- Page horizontal gutter: **36px**
- Stat-strip cell padding: **16px 24px**
- Toolbar padding: **12px 36px**
- Table row height: **46px** (single line, vertically centered)
- Cell horizontal padding: **14px** (left & right)
- Reading pane width: **460px**
- Reading pane content padding: **22px 28px 32px**
- All borders: **1px solid** the relevant token
- Border radius: **3px** (pills), **5–6px** (inputs/buttons), **6px** (cards)

---

## 2. Layout

```
┌──────────────────────────────────────────────────────────┐
│ Header: wordmark · v2.4 · local         [Openings][Settings] │
│                                          ┌──────────────┐ │
│                                          │ ▣ Reading pane│ │  ← toggle button
├──────────────────────────────────────────────────────────┤
│ Stat strip: 5 cells (Tracked / Strong match / …)         │
├──────────────────────────────────────────────────────────┤
│ Toolbar: [URL input + Enter-hint] [▶ Run all pending 4]  │
│          [All][Strong match*][Partial][No match][Errored]│
│          ─────────────────── Sort ▾  Columns ▾           │
├─────────────────────┬─────────────────────────────┬──────┤
│ FROZEN PANEL        │ SCROLL PANEL                │ READING
│  • accent stripe(4px)│ • Location                  │ PANE
│  • #                │ • Industry (hover→excerpt)  │ (460px)
│  • Company          │ • Match                     │
│  • Title            │ • Recruiter (+N alts)       │
│                     │ • Empl. (right-align)       │
│  resize handles on  │ • Remote (pill)             │
│  every column edge  │ • Status (pill)             │
│                     │ • Updated (right-align)     │
│                     │ • Actions (▶ ✎ 🗑)          │
│                     │                             │
│  vertical scroll    │ vertical scroll (synced)    │
│  shared with right  │ horizontal scroll →         │
└─────────────────────┴─────────────────────────────┴──────┘
```

### 2.1 Frozen + horizontal scroll mechanics

- Two side-by-side flex children share the same row height (46px) and use the same divider colors so the join is seamless.
- The **frozen panel** holds `accent_stripe(4px) | # | Company | Title`.
- The **scroll panel** is a `overflow-x: auto` container; the header strip above it mirrors `scrollLeft` via JS (set the header's `scrollLeft` from the body's `scroll` event).
- The frozen panel gets a soft right-edge drop shadow: `box-shadow: 4px 0 6px -4px rgba(0,0,0,0.06)` to indicate "more columns to the right."
- Vertical scroll: the **outer** container (frozen + scroll bodies side by side) scrolls vertically as one unit. Easiest implementation: put both bodies in a single scroll wrapper, with `position: sticky; left: 0` on the frozen column block.

### 2.2 Selected-row accent stripe

Render the stripe as a dedicated **4px grid column** to the left of the `#` cell (NOT as a `border-left` on the row, which crushes the leftmost cell). Empty when not selected; `background: #9a6a14` when selected.

---

## 3. Data model & API changes

### 3.1 New columns to add to `job_openings` table

Add to `init_db()` migration loop in `app.py:89`:

```python
("title",           "TEXT"),  # job title, e.g. "Director, Compliance & Risk"
("company_name",    "TEXT"),  # e.g. "Transocean"
("location",        "TEXT"),  # "Houston, TX" or "Remote — US"
("employee_count",  "TEXT"),  # stored as text to allow ranges like "5,000-10,000"
("remote_mode",     "TEXT"),  # one of: Remote, Hybrid, In-office, Other, Unspecified
```

### 3.2 Extend `EXTRACT_PROMPT` in `app.py:148`

Add these JSON keys to the contract (piggy-backs the existing single LLM call — do not add a second round-trip):

```jsonc
{
  "title":           "Verbatim job title from the posting. Empty string if not found.",
  "company_name":    "Company hiring for this role. Empty string if not found.",
  "location":        "Primary work location: 'City, ST' for US, 'Remote — US' if remote-anywhere-in-US, 'Remote — Global' if global, else best-effort. Empty string if not found.",
  "employee_count":  "Approximate global headcount of the company, formatted with commas (e.g. '5,400'). Use ranges like '1,000-5,000' if exact unknown. Empty string if not found.",
  "remote_mode":     "Exactly one of: Remote, Hybrid, In-office, Other, Unspecified."
}
```

Update `extract_fields()` parsing (`app.py:457`) and `process_opening()` UPDATE statement (`app.py:529`) to persist these fields. Update `list_openings()` SELECT (`app.py:570`) to return them.

### 3.3 Sentinels (per `Main Table Columns — Spec.md` §4.2)

- `remote_mode` empty/null = "AI hasn't run yet"; `"Unspecified"` = "AI ran but the posting didn't say"
- `industry_experience == "none"` is unchanged (means "no industry preference required")
- `employee_count == ""` = unknown; render em-dash in cell

---

## 4. Column registry (replaces existing `COLUMNS` array)

Order matters — frozen left to scroll right:

| Order | Key                  | Header     | Frozen | Sortable | Default Width | Hideable | Cell render                                                |
|------:|----------------------|------------|:------:|:--------:|--------------:|:--------:|------------------------------------------------------------|
|     1 | `accent`             | (none)     |   ✓    |    —     |          4px  |    —     | Selected-row stripe; never resizable                       |
|     2 | `id`                 | `#`        |   ✓    |    ✓     |         56px  |    ✓     | Tabular numerals, `--text-meta`                            |
|     3 | `company_name`       | `Company`  |   ✓    |    ✓     |        170px  |    ✓     | 12px / weight 500, ellipsis                                |
|     4 | `title`              | `Title`    |   ✓    |    ✓     |        240px  |    ✓     | 13px / weight 500, ellipsis                                |
|     5 | `location`           | `Location` |        |    ✓     |        130px  |    ✓     | `--text-soft`                                              |
|     6 | `industry_experience`| `Industry` |        |    ✓     |        240px  |    ✓     | Dotted-underline; **hover shows excerpt tooltip** (see §5.2) |
|     7 | `match`              | `Match`    |        |    ✓     |        100px  |    ✓     | Dot glyph + label (strong/partial/—)                       |
|     8 | `recruiter_name`     | `Recruiter`|        |    ✓     |        170px  |    ✓     | Name + `+N` chip if alternates                             |
|     9 | `employee_count`     | `Empl.`    |        |    ✓     |         90px  |    ✓     | Right-aligned, tabular numerals                            |
|    10 | `remote_mode`        | `Remote`   |        |    ✓     |        100px  |    ✓     | Color-tinted pill                                          |
|    11 | `status`             | `Status`   |        |    ✓     |        100px  |    ✓     | Color-tinted pill with leading dot                         |
|    12 | `updated_at`         | `Updated`  |        |    ✓     |         90px  |    ✓     | Relative ("2m ago"), right-aligned                         |
|    13 | `actions`            | `Actions`  |        |    —     |         92px  |    —     | `▶` `✎` `🗑` icon buttons                                  |

**Match column** is derived client-side from `industry_experience`:
- `strong` if industry text matches one of the user's saved "target industries" (future enhancement; for now hard-code "energy, healthcare, software, real estate, …" or expose in Settings)
- `partial` if any token overlap
- `none` otherwise

This is a CLIENT-SIDE computation — no backend change needed for v1. If we later store user-preferred industries server-side, move the logic there.

---

## 5. Interactions

### 5.1 Column resize (persisted)

- Each header cell has a 6px right-edge drag handle (`cursor: col-resize`).
- On `mousedown` → capture pointer, follow `mousemove` to update that column's width in component state, `mouseup` releases.
- Minimum width: **60px** (clamped).
- Persist to `localStorage`:
  - Key: `jobReviewer_v3_colWidths`
  - Value: `{ id: 56, company_name: 170, title: 240, ... }`
- Hydrate from storage on mount; merge with `DEFAULT_WIDTHS` (so newly-added columns get their default).

### 5.2 Industry-hover excerpt

- The Industry cell text gets a `border-bottom: 1px dotted #c9c2b0` to signal it's interactive.
- On `mouseenter` of the row: render a popover positioned `top: calc(100% + 4px); left: 14px;` relative to the Industry cell.
- Popover style: dark (`#1a1a1a` bg, `#fbfaf7` text), 360px wide, 12px / 14px padding, `box-shadow: 0 8px 24px rgba(0,0,0,0.25)`, border-radius 6px.
- Popover body: italic Source Serif 4, 12px, line-height 1.5. Above the body, a small uppercase eyebrow: "Excerpt — why this matched".
- Render `industry_excerpt` value verbatim. If empty, do not show the popover at all.
- Critical: parent cell needs `overflow: visible` so the popover can escape; the inner `<span>` does the ellipsis.

### 5.3 URL input behavior

- Input placeholder: `Paste a job posting URL…`
- Right-aligned hint inside input: `Press Enter to run` (`--text-faint`, 10px). **No platform-specific shortcut hint** (Windows users dominant).
- On `Enter`: `POST /api/openings { url }` then immediately `POST /api/openings/<new_id>/run`.
- On invalid URL: show inline error below the input (red text, no `alert()`).

### 5.4 Run all pending

- Toolbar button: "▶ Run all pending" with a count badge.
- Count = rows where `status == 'pending'`.
- Click: iterate, `POST /api/openings/<id>/run` for each. UI optimistically flips them to `queued`, polling updates as they progress.
- Disabled (no badge) when count is 0.

### 5.5 Reading pane toggle

- Header button "▣ Reading pane" toggles `paneOpen` state.
- Persist `paneOpen` to `localStorage` under `jobReviewer_v3_paneOpen`.
- When pane is open: the table area gets `width: calc(100% - 460px)`.
- When user clicks any table row: `selectedRowId` updates, pane re-renders with that row's data. If pane is closed, opening a row should open the pane.
- Pane close (✕ in pane header) sets `paneOpen = false` AND clears `selectedRowId`.

### 5.6 Reading pane contents

For the selected row, render:

1. **Eyebrow line** (uppercase 10px): `{company} · {location} · {employee_count} empl.` then a green/amber/gray rounded badge for the match strength.
2. **H1** (Source Serif 4, 28px): `{title}`.
3. **2×2 metadata grid** (Industry / Remote / Recruiter / Updated).
4. **Excerpt card** (white bg, border, padded): the `industry_excerpt` field in italic serif.
5. **Markdown body** (`markdown` field): rendered as plain text with `white-space: pre-wrap` (matches the existing modal behavior — do not parse markdown to HTML, the spec says raw is intentional). Use Source Serif 4 14px / 1.6.
6. **Pane header buttons:**
   - `📋` Copy markdown → writes `markdown` field to clipboard via `navigator.clipboard.writeText()`. Show "Copied" toast for 2s.
   - `↗` Open original → `window.open(url, '_blank')`.
   - `✕` Close pane.

### 5.7 Sticky table header on vertical scroll

- The table header strip (frozen + scrolling parts together) is `position: sticky; top: 0; z-index: 3` inside the scrollable body container.
- Background must be opaque (`--bg-page`) so rows scrolling under it don't bleed through.

### 5.8 Action buttons per row

Replace the current Bootstrap buttons with the icon-button style:
- 22×22, white bg, `--border-input` border, 4px radius, 10px font.
- `▶` Run extraction → `POST /api/openings/<id>/run`
- `✎` Edit URL → inline replace URL cell with input + Save/Cancel (existing edit-mode behavior, but it lives in the Reading Pane now, NOT in the row — easier UX. Open the pane and replace the URL line with an input.)
- `🗑` Delete → confirm via custom inline confirm (NOT native `confirm()`); on confirm, `DELETE /api/openings/<id>`.

For production, swap emoji glyphs for **Bootstrap Icons** (`bi-play-fill`, `bi-pencil`, `bi-trash`) — keeping with the existing icon library.

---

## 6. Files to give Claude Code

From the design project, export:

| File                              | Purpose                                                     |
|-----------------------------------|-------------------------------------------------------------|
| `Concept-1-Implementation-Spec.md` (this file) | Complete written spec — primary source of truth |
| `concept-1-console.jsx`           | Working reference implementation of the layout & interactions (read for the math, not the literal code — Flask app is plain JS, no React) |
| `Job Opening Reviewer — Concepts.html` (rendered) | Visual reference                                |
| `screenshots/concept-1-overview.png` | Full-frame screenshot at 1440×900                        |
| `screenshots/concept-1-hover-excerpt.png` | Industry hover-excerpt popover state               |
| `screenshots/concept-1-pane-open.png` | Reading pane expanded                                  |
| `screenshots/concept-1-pane-closed.png` | Reading pane collapsed (full-width table)            |

Also include the existing repo docs Claude Code already has access to:
- `UI Design Spec — As-Is.md`
- `Main Table Columns — Spec.md`
- `Job Opening Reviewer — UI Review - 2026-04-30 1117 Claude Code.md`
- `app.py`, `templates/index.html`, `requirements.txt`

---

## 7. Implementation guardrails (per existing constraints in As-Is spec §12)

- **Single-file Flask Jinja template.** No build step, no React, no Tailwind. Custom CSS in a `<style>` block at top of `templates/index.html`. Use CSS custom properties (`--bg-page`, etc.) so themes are easy.
- **Bootstrap 5 stays loaded** but its components are mostly unused now. Keep it for: modal (delete confirm if you go that way), dropdown (Sort/Columns menus), and form-control on the URL input. Override Bootstrap's defaults aggressively with custom CSS.
- **Vanilla JS only.** No jQuery. The reference JSX is for layout math; rewrite as plain ES module + DOM.
- **Bootstrap Icons 1.11.3** still used for action icons.
- **Polling interval (2s) preserved.** Pane content auto-refreshes when the selected row's status changes.
- **localStorage keys** (new):
  - `jobReviewer_v3_colWidths` — column widths
  - `jobReviewer_v3_colVis` — column visibility
  - `jobReviewer_v3_sortCol`, `jobReviewer_v3_sortAsc`
  - `jobReviewer_v3_paneOpen` — boolean
  - `jobReviewer_v3_selectedRowId` — last-viewed opening
  - Optional: `jobReviewer_v3_targetIndustries` — comma-separated user preferences for the Match calculation

---

## 8. Acceptance checklist

- [ ] Five new DB columns (`title`, `company_name`, `location`, `employee_count`, `remote_mode`) added via `ALTER TABLE` migration; existing rows tolerate NULLs.
- [ ] `EXTRACT_PROMPT` extended with the five new JSON keys; `extract_fields()` parses them; `process_opening()` persists them.
- [ ] Frozen left panel: #, Company, Title. Scrolling right panel: everything else. Sticky header on vertical scroll.
- [ ] Every column resizable; widths persist across reloads.
- [ ] Selected-row accent stripe is its own 4px lane, not a border on the # cell.
- [ ] All cells vertically centered at 46px row height; status pills, remote pills, match dots align.
- [ ] Industry cell hover shows verbatim-excerpt popover when `industry_excerpt` is non-empty.
- [ ] Reading pane opens on row click; ✕ closes; toggle button reflects state; pane state persists across reloads.
- [ ] Pane Copy button writes `markdown` to clipboard; Open button opens `url` in new tab.
- [ ] URL input runs on Enter; "Run all pending" iterates pending rows.
- [ ] Toolbar filters update the visible row set client-side.
- [ ] Color, status, and remote pill values match §1.1.
- [ ] No native `alert()` / `confirm()` anywhere — all confirmations are inline.
- [ ] Page renders cleanly at 1280px viewport (horizontal scroll appears in the right panel; frozen panel + reading pane remain usable).
