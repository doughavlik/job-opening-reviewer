# Job Opening Reviewer — As-Is UI Design Spec

> **Purpose of this doc.** A complete, self-contained description of the current UI so a design tool (e.g. Claude Design) can ingest it and propose multiple alternative visual directions. It captures *what exists today*, the underlying data and interactions, and the constraints any redesign must respect — but does **not** prescribe a visual direction.
>
> **Companion doc.** [`Job Opening Reviewer — UI Review - 2026-04-30 1117 Claude Code.md`](Job%20Opening%20Reviewer%20%E2%80%94%20UI%20Review%20-%202026-04-30%201117%20Claude%20Code.md) is a critique of the same UI with prioritized fixes. Use that for "what's wrong"; use this doc for "what's there."
>
> **Source of truth.** The entire UI is one file: [`templates/index.html`](templates/index.html). All HTML, CSS, and JS quoted below is from that file.

---

## 1. Product context

- **App name:** Job Opening Reviewer
- **What it does:** Local Flask single-page tool. Paste a job-opening URL, the backend fetches it, converts the page to markdown via Gemini, and extracts (a) required industry experience, (b) a supporting excerpt, (c) the recruiter (name, title, LinkedIn, email) plus alternates, all written back into a SQLite row. The UI is the only way to drive this — there is no CLI.
- **Audience:** A single power-user (the developer / job-seeker) working on a desktop browser. Not multi-tenant, no auth.
- **Deployment surface:** Served by Flask at `http://localhost:5000`.
- **Technology baseline:**
  - Bootstrap 5.3.2 (CSS + JS bundle) loaded from CDN.
  - Bootstrap Icons 1.11.3 from CDN.
  - No build step, no framework, no component library beyond Bootstrap. ~700 lines of vanilla JS in a `<script>` block.
  - Persists user prefs (sort, column visibility, column widths) in `localStorage`.
  - Polls `/api/openings` every 2 s while any row is `queued` or `running`.

---

## 2. Information architecture

```
Page (single route /)
├── Page header        "Job Opening Reviewer" with briefcase icon
├── Tab bar            [Job Openings] [Settings]
│
├── Tab 1: Job Openings (default active)
│   ├── Toolbar        [+ Add Job Opening] [↻ Refresh] [▦ Columns ▾]
│   ├── Inline add card (initially hidden, slides in below toolbar)
│   │     URL input + [Save] [Cancel]
│   └── Data table
│         Columns: # · Job Opening URL · Industry Experience · Excerpt
│                  · Recruiter · Status · Job Description · Actions
│
├── Tab 2: Settings
│   ├── Card: Google Gemini API key (password input + status line)
│   ├── Card: Anthropic API key (password input + status line)
│   └── [Save] button
│
├── Modal: Recruiter (primary + alternates list)
└── Modal: Markdown content (Job Description / Excerpt full text + Copy)
```

Two tabs, one main table, two modals, one inline form. No router, no separate pages, no detail view per opening. State is in JS module-scoped variables; nothing in URL.

---

## 3. Page chrome

### 3.1 Container & spacing

```html
<body style="padding-top: 1.5rem">
  <div class="container-fluid px-4">
    ...
  </div>
</body>
```

- `.container-fluid` has **no max-width**, so on a 4K monitor the table spans edge-to-edge.
- `px-4` = 1.5 rem horizontal gutter.
- 1.5 rem padding above the H1.

### 3.2 Header

```html
<h1 class="mb-3"><i class="bi bi-briefcase"></i> Job Opening Reviewer</h1>
```

- Bootstrap default H1 (~2.5 rem, system font stack).
- Briefcase icon inline before the wordmark, same color as text.
- No subtitle, no logo, no nav, no user/account chrome.

### 3.3 Tab bar

```html
<ul class="nav nav-tabs">
  <li class="nav-item"><button class="nav-link active">Job Openings</button></li>
  <li class="nav-item"><button class="nav-link">Settings</button></li>
</ul>
```

- Standard Bootstrap pill-less underline tabs.
- Active tab is **not** persisted across reloads.
- Tab content sits in a `.tab-content.pt-3` (1 rem top padding from tab bar).

---

## 4. Tab 1: Job Openings

### 4.1 Toolbar

A single-row flex strip above the table:

| Button | Style | Icon | Behaviour |
|---|---|---|---|
| Add Job Opening | `btn btn-primary` | `bi-plus-lg` | Reveals the inline add-card below the toolbar |
| Refresh | `btn btn-outline-secondary` | `bi-arrow-clockwise` | Re-fetches `/api/openings` |
| Columns ▾ | `btn btn-outline-secondary dropdown-toggle` | `bi-layout-three-columns` | Dropdown of checkboxes, one per hideable column |

The toolbar is `d-flex gap-2 align-items-center flex-wrap mb-3`. It does not stick on scroll.

### 4.2 Inline add form

Hidden by default (`d-none`), shown when **Add Job Opening** is clicked. Pushes the table down — does not overlay.

```html
<div id="addForm" class="card mb-3 d-none">
  <div class="card-body">
    <div class="input-group">
      <input type="url" class="form-control" placeholder="https://example.com/jobs/12345">
      <button class="btn btn-success">Save</button>
      <button class="btn btn-outline-secondary">Cancel</button>
    </div>
  </div>
</div>
```

Single URL input, no validation beyond `type="url"`, no notion of bulk add or paste-list.

### 4.3 The data table — structure

Markup:

```html
<div style="overflow-x: auto">
  <table id="openingsTable" class="table table-hover align-middle">
    <thead class="table-light"><tr> ...8 <th> cells... </tr></thead>
    <tbody id="openingsBody"></tbody>
  </table>
</div>
```

CSS that drives layout:

```css
#openingsTable { table-layout: fixed; width: 100%; }
#openingsTable th { position: relative; overflow: hidden; white-space: nowrap; }
.resize-handle { position: absolute; right: 0; top: 0; width: 5px; height: 100%; cursor: col-resize; }
```

- **Fixed table layout.** Each `<th>` has its width set in JS from `colWidths` (persisted) or `defaultWidth`. Sum of defaults ≈ 1,320 px.
- **Inner horizontal scroll** kicks in when the table is wider than its `overflow-x: auto` wrapper.
- **Per-column resize handle** (5 px sliver on the right edge of each header). Drag to resize, persists in `localStorage`.
- **No sticky header.**
- `table-hover` highlights the hovered row in a faint gray.

### 4.4 The data table — columns

Eight columns, declared once in JS and used to build both the table headers and the column-visibility menu:

| # | Key | Header label | Sortable | Hideable | Default width | Cell content |
|---|---|---|---|---|---|---|
| 1 | `id` | `#` | yes | yes | 50 px | Plain integer |
| 2 | `url` | `Job Opening URL` | yes | yes | 220 px | `<a target="_blank">` truncated to 320 px wide via `.truncate { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }` |
| 3 | `industry_experience` | `Industry Experience` | yes | yes | 160 px | Free-form short string (e.g. "5+ years in SaaS sales") |
| 4 | `industry_excerpt` | `Excerpt` | no | yes | 200 px | 2-line clamped teaser + `[👁 View]` button → opens markdown modal |
| 5 | `recruiter` | `Recruiter` | yes (by `recruiter_name`) | yes | 200 px | Name + LinkedIn icon link + `+N` badge if alternates; whole cell click opens recruiter modal |
| 6 | `status` | `Status` | yes | yes | 90 px | Lowercase word, **color-only** (`pending` gray / `queued` blue / `running` cyan / `done` green / `error` red) |
| 7 | `markdown` | `Job Description` | no | yes | 260 px | 2-line clamped teaser + `[👁 View]` button → opens markdown modal; em-dash placeholder if empty |
| 8 | `actions` | `Actions` | no | **no** | 280 px | `[▶ Run Now]` `[✎]` `[🗑]` row-level buttons |

Sort is client-side (in-memory `Array.sort` over `openings`), persisted as `sortCol` / `sortAsc` in `localStorage`. The active sort header gets a `▲` / `▼` glyph appended via `::after` content.

### 4.5 The data table — text-content styling

```css
.truncate         { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.excerpt          { font-size: 0.85rem; color: #555; max-width: 420px; }
.markdown-teaser  { font-size: 0.78rem; color: #444; white-space: pre-wrap; overflow: hidden;
                    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.excerpt .markdown-teaser { font-size: 0.85rem; color: #555; }
.job-desc-cell    { min-width: 220px; max-width: 320px; }
```

Two distinct text scales: 0.85 rem for excerpt, 0.78 rem for the JD teaser. Both fade to mid-gray (`#555` / `#444`).

### 4.6 The data table — status pill (currently text-only)

```css
.status-pending { color: #6c757d; }   /* Bootstrap secondary gray */
.status-queued  { color: #0d6efd; }   /* Bootstrap primary blue   */
.status-running { color: #0dcaf0; }   /* Bootstrap info cyan      */
.status-done    { color: #198754; }   /* Bootstrap success green  */
.status-error   { color: #dc3545; }   /* Bootstrap danger red     */
```

Status is rendered as a single colored word. No icon, no badge, no background. Errors get the message in the `title` tooltip.

### 4.7 The data table — recruiter cell

Compact in-cell rendering:

- Primary recruiter **name** in default body text (or `(unnamed)` muted small if missing).
- LinkedIn icon link if `recruiter_linkedin` set (`<i class="bi bi-linkedin"></i>`, no label).
- `+N` badge (`badge bg-secondary ms-2`) when alternates exist.
- Whole wrapper has `cursor: pointer` and `title="Click to see alternate recruiters"` — clicks open the recruiter modal.
- LinkedIn link `stopPropagation`s so it opens externally instead of the modal.

### 4.8 The data table — actions cell

Three icon-with-text buttons, side by side:

```html
<button class="btn btn-sm btn-outline-primary me-1 btn-run">
  <i class="bi bi-play-fill"></i> Run Now
</button>
<button class="btn btn-sm btn-outline-secondary me-1 btn-edit"
        title="Edit"><i class="bi bi-pencil"></i></button>
<button class="btn btn-sm btn-outline-danger btn-del"
        title="Delete"><i class="bi bi-trash"></i></button>
```

- "Run Now" button uses an icon **and** a label (the only such button in the row); the other two are icon-only with `title` tooltips.
- Default column width 280 px to fit them; on a wide monitor leftover space inflates the column further (table-layout-fixed proportional growth).

### 4.9 Empty / loading / error states

- **Empty database:** the `<tbody>` simply renders zero rows. No empty-state copy, no illustration, no CTA repeating "Add Job Opening."
- **In-flight rows:** the row's status cell reads `queued` or `running`. The row keeps its old data underneath. There is no spinner, no progress bar, no row-level disabled state. The table polls every 2 s and re-renders when status changes.
- **Per-row error:** status text turns red and reads `error`; the full error message lives in the `title` tooltip on the cell. Nothing else in the row indicates the failure.
- **Network errors on user actions** (Add, Edit, Delete, Run, Save settings): a native `alert()` dialog with `"Action failed: " + e.message`.
- **Delete confirmation:** native `confirm("Delete this job opening?")` — visually inconsistent with the rest of the app.

---

## 5. Tab 2: Settings

```html
<div class="card mb-3" style="max-width: 560px;">
  <div class="card-body">
    <h5 class="card-title">Google Gemini API key</h5>
    <p class="text-muted small">Used for HTML→markdown conversion. Stored locally in SQLite. Leave blank to keep the current value.</p>
    <div class="mb-3">
      <label class="form-label">API key</label>
      <input type="password" class="form-control" autocomplete="off">
      <div class="form-text" id="apiKeyStatus"></div>
    </div>
  </div>
</div>
<!-- identical card for Anthropic API key -->
<button class="btn btn-primary" id="saveSettings">Save</button>
```

- Two visually identical cards stacked vertically, max-width 560 px, left-aligned (no centering on wide screens).
- Each card: card title, helper paragraph (`text-muted small`), labelled password input, status line below the input.
- Status line shows `Saved key starts with: AIza…` if a key is set, else `No key set.` (Prefix is the first 7 characters, returned by the backend.)
- Single primary `[Save]` button below both cards saves both at once.
- Confirmation is a native `alert("Settings saved.")`.
- The Settings tab does **not** lazy-load until first activated (`shown.bs.tab` event), so its first paint can lag a moment.

---

## 6. Modals

Both modals are standard Bootstrap 5 modals with header / body / footer.

### 6.1 Recruiter modal

```
┌──────────────────────────────────────────┐
│ 🪪 Recruiters                          ✕ │
├──────────────────────────────────────────┤
│ Primary recruiter                        │
│ **Name**                                 │
│ small muted title line                   │
│ in LinkedIn · ✉ email@host               │
│                                          │
│ Alternate recruiters                     │
│ • Name                                   │
│   small muted title line                 │
│   in LinkedIn · ✉ email                  │
│ • Name …                                 │
├──────────────────────────────────────────┤
│                              [ Close ]   │
└──────────────────────────────────────────┘
```

- Default Bootstrap modal width (`modal-dialog`, ~500 px).
- "Primary" name in `<strong>`; alternates in plain `<span>` with bullet list (`list-unstyled`).
- LinkedIn link uses the `bi-linkedin` icon + word "LinkedIn"; email link uses `bi-envelope` + the address.
- "No alternates suggested." muted line if the alternates array is empty.

### 6.2 Markdown modal (Job Description / Excerpt)

```
┌──────────────────────────────────────────┐
│ 📄 Job Description                     ✕ │
├──────────────────────────────────────────┤
│ <pre> full markdown, monospace-fallback  │
│  but actually `font-family: inherit`,    │
│  `white-space: pre-wrap`, scrollable     │
│  inside the modal                        │
│ </pre>                                   │
├──────────────────────────────────────────┤
│ [📋 Copy] [Close]                        │
└──────────────────────────────────────────┘
```

- Wider variant: `modal-lg modal-dialog-scrollable` (~800 px).
- Title swaps to "Industry Excerpt" when opened from the Excerpt cell.
- Body is a `<pre class="markdown-modal-body">` styled to **inherit** body font (so it looks like prose, not code) but preserve whitespace via `pre-wrap`.
- Copy button switches its label to `[✓ Copied!]` for 2 s on success.
- Markdown is rendered **as raw text** (headings, lists, links not parsed). This is intentional — the "markdown" is what the LLM emitted and may include scaffolding the user wants to inspect verbatim.

---

## 7. Visual design — current palette & type

The app uses Bootstrap 5.3 defaults end-to-end. No custom theme, no CSS variables overridden.

| Token | Value | Where it's used |
|---|---|---|
| Primary | `#0d6efd` | Add / Save Settings buttons, queued status, Run Now outline |
| Success | `#198754` | Save (add form) button, done status |
| Danger | `#dc3545` | Delete outline, error status |
| Info | `#0dcaf0` | Running status |
| Secondary | `#6c757d` | Pending status, alternates badge, Refresh / Columns / Cancel outlines, muted helper text |
| Body color | `#212529` | All primary text |
| Body bg | `#fff` | Page |
| Table header bg | `--bs-table-bg` from `.table-light` (light gray) | `<thead class="table-light">` |
| Excerpt text | `#555` | `.excerpt` |
| JD teaser text | `#444` | `.markdown-teaser` |
| Resize handle hover | `rgba(0,0,0,0.15)` | 5-px column resizer |

Typography is the Bootstrap stack (system UI sans). Sizes:

- H1: ~2.5 rem
- H5 (card titles): ~1.25 rem
- H6 (modal sub-headers): ~1 rem
- Body: 1 rem / `#212529`
- Excerpt: 0.85 rem / `#555`
- JD teaser: 0.78 rem / `#444`
- Modal body `<pre>`: 0.9 rem, inherits body family
- Bootstrap small (`.small`, `.text-muted small`, `form-text`): 0.875 rem

Spacing is Bootstrap utility classes only (`mb-3`, `mt-1`, `me-1`, `gap-2`, `pt-3`).

Iconography: Bootstrap Icons 1.11.3, monoline outline style. Icons in use:
`bi-briefcase`, `bi-plus-lg`, `bi-arrow-clockwise`, `bi-layout-three-columns`,
`bi-eye`, `bi-person-badge`, `bi-linkedin`, `bi-envelope`, `bi-file-text`,
`bi-clipboard`, `bi-clipboard-check`, `bi-play-fill`, `bi-pencil`, `bi-trash`.

No imagery, no illustrations, no logo, no avatars.

---

## 8. Interactions & motion

- **Add → reveal inline card.** No animation; the card simply un-hides and pushes the table down.
- **Edit → inline cell replacement.** The URL cell becomes an input; the actions cell becomes Save / Cancel. Other cells in the row stay put.
- **Delete → native `confirm()`** then optimistic refetch.
- **Run Now → POST then refetch.** Row's status flips to `queued` then `running`; the 2-s poller updates it.
- **Sort header click → toggle direction**, persist, re-render.
- **Column drag handle** for resize; **column dropdown** for show/hide. Both persist to `localStorage`.
- **Recruiter cell → click opens modal.**
- **Excerpt / JD `[View]` → click opens markdown modal.**
- **Settings → Save → native `alert("Settings saved.")`**, then refresh status lines.
- **Polling.** `setInterval(pollIfRunning, 2000)` re-fetches `/api/openings` only when at least one row is queued/running. No visible polling indicator.

No transitions, no skeletons, no toasts, no progress bars, no optimistic UI beyond Bootstrap's native button focus states.

---

## 9. Responsive behaviour

There is essentially **no responsive design**.

- Container width is unbounded above and identical below — no breakpoints affect layout.
- The table has `table-layout: fixed; width: 100%` with `defaultWidth` summing to ~1,320 px. Below ~1,320 px viewport, the inner `overflow-x: auto` produces a side-scroll strip; the page itself doesn't reflow.
- On a docked / half-width window (~600 px) the user side-scrolls a 600-px window through a 1,460-px-wide table. Header doesn't stick. Nothing collapses to a single-column layout.
- On a 4K monitor the Action column inflates to ~600 px around three small icon buttons because the fixed-layout engine distributes leftover width proportionally.

---

## 10. Accessibility — current state

- All controls are real `<button>` / `<a>` / `<input>` elements (no `div` buttons).
- Bootstrap modals carry `tabindex="-1"`, `aria-hidden`, `aria-label` close buttons.
- `<th>` cells use proper table semantics; sort columns have visual indicators but no `aria-sort` attribute.
- **Status is communicated by color alone** — color-blind users have no fallback (no icon, no shape, no label change).
- Resize handles have no keyboard equivalent.
- The recruiter and markdown modals are reachable by keyboard.
- No skip-to-main, no landmarks, no `<main>` / `<nav>`.

---

## 11. Data fields shown in the UI (for redesign reference)

Per opening row, the API returns:

```jsonc
{
  "id": 7,                                     // integer PK
  "url": "https://...",                        // job posting URL
  "markdown": "## About the role\n...",        // long string, can be 3–12 KB
  "industry_experience": "5+ years SaaS",      // short free-form string, 0–80 chars typical
  "industry_excerpt": "We're looking for...",  // 1–4 sentences, ~50–400 chars
  "status": "pending|queued|running|done|error",
  "error": "TimeoutError: ...",                // only set on error
  "recruiter_name": "Jane Doe",
  "recruiter_title": "Senior Technical Recruiter",
  "recruiter_linkedin": "https://linkedin.com/in/janedoe",
  "recruiter_email": "jane@company.com",
  "alternate_recruiters": "[{\"name\":\"...\",\"title\":\"...\",...}, ...]"
                                               // JSON string array of {name,title,linkedin,email}
}
```

A redesign needs to find a place for **all of these** when present, and degrade gracefully when absent. The most space-hungry are `markdown` and `industry_excerpt`; the most identity-laden is the recruiter object.

---

## 12. Constraints any redesign must respect

1. **Single static HTML file** rendered by Flask Jinja, plus Bootstrap 5 CSS/JS and Bootstrap Icons from CDN. No build step. **No npm, no React, no Tailwind, no Sass.** A redesign is welcome to introduce a small amount of custom CSS, but should keep the "drop the file in `templates/` and refresh" workflow.
2. **Bootstrap 5 components are preferred over hand-rolled equivalents** where they fit (modal, dropdown, card, tab, table, form-control). Adding a second component framework is out of scope.
3. **Vanilla JS only** (`fetch`, DOM APIs, no jQuery despite Bootstrap's history).
4. **Local-only, single-user.** No login, no theme switcher needs to persist server-side, no multi-tenant.
5. **localStorage prefs must survive:** sort column, sort direction, column visibility, column widths. (A redesign can drop the per-column resize handles if it proposes a different density model.)
6. **Polling is API-driven** (status field). The redesign should keep status visible enough that the user notices when a long-running fetch finishes.
7. **Backend API is fixed** (`GET/POST/PUT/DELETE /api/openings`, `POST /api/openings/<id>/run`, `GET/PUT /api/settings`). Redesign cannot assume new endpoints.
8. **Browser support:** modern Chromium on desktop; the user's primary environment. No IE11, no mobile-first requirement, but graceful behaviour at 600–800 px wide is desirable for "left-docked window" use.

---

## 13. What the redesign should be free to change

- Color palette, typography, spacing scale (Bootstrap defaults are not load-bearing).
- Layout primitive for the list of openings — table is the current choice but cards, list-with-detail-pane, kanban-by-status, etc. are all on the table.
- Treatment of long content (markdown, excerpt) — modal vs. detail drawer vs. dedicated route vs. expandable row.
- Status visualization — color-only word vs. badge vs. icon vs. step indicator.
- Density / row height model — fixed clamped vs. user-toggleable density vs. card grid.
- Empty / loading / error states — currently absent; greenfield for the designer.
- Modal vs. inline patterns for Add / Edit / Delete confirm.
- Sticky headers / sticky toolbar / responsive collapse rules.
- Tab navigation — could become a sidebar, a top-nav, or settings could move to a gear icon + drawer.

---

## 14. Goals for the redesign options

Provide **multiple distinct directions**, each internally consistent. For each, please cover:

1. **Visual mood** in one sentence (e.g. "calm reading-app", "dense ops dashboard", "soft consumer SaaS").
2. **Layout primitive** for the openings list (table vs. cards vs. list-detail vs. board).
3. **How long markdown is read** — full-screen, side panel, modal, dedicated route.
4. **Status treatment** — make it pop, or de-emphasize it.
5. **Recruiter treatment** — peer of the row, drawer, popover, dedicated section.
6. **Settings treatment** — separate tab, drawer, modal, gear icon.
7. **A representative sketch / wireframe** at desktop-wide, desktop-docked-narrow, and (if relevant) one detail view.

The directions can disagree with each other. Surprise is welcome. The current UI is a competent Bootstrap admin table; the goal is to find shapes that aren't that.
