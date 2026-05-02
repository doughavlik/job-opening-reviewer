/* Concept 1 v3 — Operations Console
   - Frozen left panel (#, Company, Title) + scrolling right panel (rest of columns)
     Both share the same row template so values line up across the divide.
   - Each column has an explicit width in state, persisted to localStorage
     ('jobReviewer_v3_colWidths'), and a 6px right-edge resize handle.
   - Selected-row accent stripe is its own grid track (8px) so it never crushes the # cell.
   - All cells use consistent vertical alignment + tabular numerals where appropriate.
*/

const STORAGE_KEY = 'jobReviewer_v3_colWidths';

const DEFAULT_WIDTHS = {
  // frozen
  id: 56, co: 170, title: 240,
  // scroll
  loc: 130, industry: 240, match: 100, recruiter: 170,
  emp: 90, remote: 100, status: 100, time: 90, actions: 92,
};

const FROZEN_COLS = ['id', 'co', 'title'];
const SCROLL_COLS = ['loc', 'industry', 'match', 'recruiter', 'emp', 'remote', 'status', 'time', 'actions'];

const useColWidths = () => {
  const [widths, setWidths] = React.useState(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
      return { ...DEFAULT_WIDTHS, ...saved };
    } catch { return DEFAULT_WIDTHS; }
  });
  React.useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(widths)); } catch {}
  }, [widths]);
  return [widths, setWidths];
};

const ResizeHandle = ({ onDrag }) => {
  const onMouseDown = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const move = (ev) => onDrag(ev.clientX - startX);
    const up = () => {
      window.removeEventListener('mousemove', move);
      window.removeEventListener('mouseup', up);
    };
    window.addEventListener('mousemove', move);
    window.addEventListener('mouseup', up);
  };
  return (
    <span
      onMouseDown={onMouseDown}
      style={{
        position: 'absolute', top: 0, right: -3, width: 6, height: '100%',
        cursor: 'col-resize', zIndex: 5,
      }}
    />
  );
};

const Concept1 = () => {
  const [paneOpen, setPaneOpen] = React.useState(true);
  const [hoverRow, setHoverRow] = React.useState(null);
  const [widths, setWidths] = useColWidths();

  const rows = [
    { id: 142, co: 'Transocean', title: 'Director, Compliance & Risk', loc: 'Houston, TX', emp: '5,400', remote: 'Hybrid', industries: 'energy, offshore drilling, regulatory', excerpt: '"Minimum 10 years\' experience in offshore drilling, energy, or heavily-regulated industries. Familiarity with BSEE, ABS, and IMO frameworks required."', match: 'strong', status: 'done', recruiter: 'Marisol Vega', alts: 2, time: '2m ago' },
    { id: 141, co: 'Memorial Hermann', title: 'VP, Revenue Cycle', loc: 'Houston, TX', emp: '28,000', remote: 'In-office', industries: 'healthcare, hospital ops, RCM', excerpt: '"7+ years leading revenue cycle operations in a hospital system; deep familiarity with Epic Resolute and CMS regulations."', match: 'partial', status: 'done', recruiter: 'James Okafor', alts: 3, time: '14m ago' },
    { id: 140, co: 'Sysco', title: 'Head of FP&A — Foodservice', loc: 'Houston, TX', emp: '76,000', remote: 'Hybrid', industries: 'foodservice, distribution, wholesale', excerpt: '"Prior FP&A leadership in foodservice, broadline distribution, or wholesale CPG strongly preferred."', match: 'partial', status: 'running', recruiter: '—', alts: 0, time: 'now' },
    { id: 139, co: 'Quanta Services', title: 'GM, Renewable Infrastructure', loc: 'Houston, TX', emp: '52,000', remote: 'In-office', industries: 'energy, EPC, utilities', excerpt: '"15+ years in EPC, utility-scale renewable construction, or transmission infrastructure."', match: 'strong', status: 'done', recruiter: 'Linh Pham', alts: 1, time: '1h ago' },
    { id: 138, co: 'Stewart Title', title: 'Chief Operating Officer', loc: 'Houston, TX', emp: '6,800', remote: 'In-office', industries: 'title insurance, real estate', excerpt: '"Executive operations experience inside a title or real-estate services firm strongly preferred."', match: 'none', status: 'done', recruiter: '(unnamed)', alts: 0, time: '3h ago' },
    { id: 137, co: 'Cheniere Energy', title: 'Senior Counsel, LNG', loc: 'Houston, TX', emp: '1,650', remote: 'Hybrid', industries: 'energy, LNG, regulatory, legal', excerpt: '"JD with 8+ years in LNG, FERC, or DOE regulatory practice required."', match: 'strong', status: 'queued', recruiter: 'Pending', alts: 0, time: 'queued' },
    { id: 136, co: 'BMC Software', title: 'VP Product, Mainframe', loc: 'Remote — US', emp: '6,000', remote: 'Remote', industries: 'enterprise software, mainframe', excerpt: '"Mainframe (z/OS) product leadership experience required; large-enterprise GTM background a plus."', match: 'partial', status: 'error', recruiter: '—', alts: 0, time: '6h ago' },
    { id: 135, co: 'Halliburton', title: 'Director, Digital Solutions', loc: 'Houston, TX', emp: '48,000', remote: 'Hybrid', industries: 'oilfield services, energy tech', excerpt: '"Background in oilfield services, energy tech, or industrial SaaS for upstream operators required."', match: 'strong', status: 'done', recruiter: 'Diane Wexler', alts: 2, time: '1d ago' },
    { id: 134, co: 'Group 1 Auto', title: 'Regional GM, Gulf Coast', loc: 'Houston, TX', emp: '14,500', remote: 'In-office', industries: 'auto retail, dealership ops', excerpt: '"Multi-store dealership P&L leadership required."', match: 'partial', status: 'done', recruiter: 'Carlos Mendez', alts: 1, time: '1d ago' },
    { id: 133, co: 'Hines', title: 'MD, Industrial Capital', loc: 'Houston, TX', emp: '4,800', remote: 'Hybrid', industries: 'commercial real estate, industrial', excerpt: '"10+ years sourcing industrial / logistics CRE capital."', match: 'partial', status: 'done', recruiter: 'Aisha Khan', alts: 2, time: '2d ago' },
  ];

  const setW = (key, dx) => setWidths(w => ({ ...w, [key]: Math.max(60, (w[key] || DEFAULT_WIDTHS[key]) + dx) }));

  const matchColor = (m) => m === 'strong' ? '#0d6e54' : m === 'partial' ? '#9a6a14' : m === 'none' ? '#9a9893' : '#9a9893';
  const matchDot = (m) => m === 'strong' ? '●' : m === 'partial' ? '◐' : m === 'none' ? '○' : '○';

  const remoteStyle = (r) => {
    const map = {
      'Remote': { c: '#0d6e54', bg: '#e8efe8' },
      'Hybrid': { c: '#3a558a', bg: '#e6ecf5' },
      'In-office': { c: '#7a6a4a', bg: '#f0ebe0' },
      'Other': { c: '#8b8676', bg: '#f5f2ec' },
      'Unspecified': { c: '#a8a39a', bg: '#f5f2ec' },
    };
    return map[r] || map.Unspecified;
  };

  const selected = 142;
  const ROW_H = 46;
  const ACCENT_W = 4;

  // Build grid template strings
  const frozenTemplate = `${ACCENT_W}px ${widths.id}px ${widths.co}px ${widths.title}px`;
  const scrollTemplate = SCROLL_COLS.map(k => `${widths[k]}px`).join(' ');

  // Header cell helper
  const HeaderCell = ({ label, k, align = 'left' }) => (
    <div style={{
      position: 'relative', padding: '0 14px',
      display: 'flex', alignItems: 'center',
      justifyContent: align === 'right' ? 'flex-end' : 'flex-start',
      fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em',
      color: '#8b8676', userSelect: 'none', whiteSpace: 'nowrap',
    }}>
      <span>{label}</span>
      {k && <ResizeHandle onDrag={(dx) => setW(k, dx)} />}
    </div>
  );

  // Scrollable wrapper ref to sync header + body horizontal scroll
  const headScrollRef = React.useRef(null);
  const bodyScrollRef = React.useRef(null);
  const onBodyScroll = (e) => {
    if (headScrollRef.current) headScrollRef.current.scrollLeft = e.target.scrollLeft;
  };

  return (
    <div style={{
      width: 1440, height: 900, background: '#fbfaf7', color: '#1a1a1a',
      fontFamily: '"Inter", system-ui, sans-serif', display: 'flex', flexDirection: 'column',
      position: 'relative', overflow: 'hidden',
    }}>
      {/* Top bar */}
      <header style={{
        display: 'flex', alignItems: 'center', padding: '20px 36px',
        borderBottom: '1px solid #e8e4dc', gap: 32,
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
          <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: 19, fontWeight: 600, letterSpacing: '-0.01em' }}>
            Job Opening Reviewer
          </div>
          <div style={{ fontSize: 12, color: '#8b8676', marginLeft: 6 }}>v2.4 · local</div>
        </div>
        <nav style={{ display: 'flex', gap: 4, marginLeft: 'auto', fontSize: 13, alignItems: 'center' }}>
          {['Openings', 'Settings'].map((t, i) => (
            <div key={t} style={{
              padding: '6px 14px', borderRadius: 6,
              background: i === 0 ? '#1a1a1a' : 'transparent',
              color: i === 0 ? '#fbfaf7' : '#3a3a3a',
              fontWeight: i === 0 ? 500 : 400,
            }}>{t}</div>
          ))}
          <div style={{ width: 1, height: 18, background: '#e8e4dc', margin: '0 10px' }}></div>
          <div
            onClick={() => setPaneOpen(!paneOpen)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', borderRadius: 6,
              border: '1px solid #e0dccf', background: paneOpen ? '#1a1a1a' : '#fff',
              color: paneOpen ? '#fbfaf7' : '#3a3a3a', cursor: 'pointer', fontSize: 12,
            }}
          >
            <span style={{ fontSize: 11 }}>{paneOpen ? '▣' : '▢'}</span>
            Reading pane
          </div>
        </nav>
      </header>

      {/* Stat strip */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', borderBottom: '1px solid #e8e4dc' }}>
        {[
          { k: 'Tracked', v: '142', s: '+8 this week' },
          { k: 'Strong match', v: '34', s: 'industry overlap' },
          { k: 'Awaiting recruiter', v: '11', s: 'web search pending' },
          { k: 'Errored', v: '3', s: 'review fetch logs' },
          { k: 'Avg. extract time', v: '7.2s', s: 'last 50 runs' },
        ].map((s, i) => (
          <div key={i} style={{ padding: '16px 24px', borderRight: i < 4 ? '1px solid #e8e4dc' : 'none' }}>
            <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#8b8676', marginBottom: 6 }}>{s.k}</div>
            <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: 26, fontWeight: 600, letterSpacing: '-0.02em', lineHeight: 1 }}>{s.v}</div>
            <div style={{ fontSize: 11, color: '#8b8676', marginTop: 5 }}>{s.s}</div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '12px 36px',
        borderBottom: '1px solid #e8e4dc', background: '#f5f2ec',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px',
          background: '#fff', border: '1px solid #e0dccf', borderRadius: 6, width: 380, fontSize: 13, color: '#8b8676',
        }}>
          <span>⌕</span> Paste a job posting URL…
          <span style={{ marginLeft: 'auto', fontSize: 10, color: '#a8a39a' }}>Press Enter to run</span>
        </div>
        <div style={{
          padding: '7px 12px', background: '#1a1a1a', color: '#fbfaf7', borderRadius: 6,
          fontSize: 12, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span>▶</span> Run all pending
          <span style={{ padding: '1px 6px', background: '#3a3a3a', borderRadius: 3, fontSize: 10 }}>4</span>
        </div>
        <div style={{ display: 'flex', gap: 6, fontSize: 12, marginLeft: 8 }}>
          {['All', 'Strong match', 'Partial', 'No match', 'Errored'].map((f, i) => (
            <div key={f} style={{
              padding: '6px 11px', borderRadius: 5,
              background: i === 1 ? '#1a1a1a' : 'transparent',
              color: i === 1 ? '#fbfaf7' : '#3a3a3a',
            }}>{f}</div>
          ))}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, fontSize: 12, color: '#3a3a3a' }}>
          <span>Sort: Newest ▾</span><span>·</span><span>Columns ▾</span>
        </div>
      </div>

      {/* Main row */}
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* Table */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
          {/* Header row (frozen left + scroll right that mirrors body) */}
          <div style={{ display: 'flex', borderBottom: '1px solid #e8e4dc', background: '#fbfaf7' }}>
            {/* Frozen header */}
            <div style={{
              display: 'grid', gridTemplateColumns: frozenTemplate,
              height: 38, flexShrink: 0,
              borderRight: '1px solid #e8e4dc',
              boxShadow: '4px 0 6px -4px rgba(0,0,0,0.06)',
              zIndex: 3,
            }}>
              <div></div>
              <HeaderCell label="#" k="id" />
              <HeaderCell label="Company" k="co" />
              <HeaderCell label="Title ▼" k="title" />
            </div>
            {/* Scroll header (mirrors body scroll) */}
            <div ref={headScrollRef} style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ display: 'grid', gridTemplateColumns: scrollTemplate, height: 38 }}>
                <HeaderCell label="Location" k="loc" />
                <HeaderCell label="Industry" k="industry" />
                <HeaderCell label="Match" k="match" />
                <HeaderCell label="Recruiter" k="recruiter" />
                <HeaderCell label="Empl." k="emp" align="right" />
                <HeaderCell label="Remote" k="remote" />
                <HeaderCell label="Status" k="status" />
                <HeaderCell label="Updated" k="time" align="right" />
                <HeaderCell label="Actions" k="actions" align="right" />
              </div>
            </div>
          </div>

          {/* Body */}
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
            {/* Frozen body */}
            <div style={{
              flexShrink: 0,
              borderRight: '1px solid #e8e4dc',
              boxShadow: '4px 0 6px -4px rgba(0,0,0,0.06)',
              zIndex: 2, background: '#fbfaf7',
              overflowY: 'auto', overflowX: 'hidden',
            }}>
              {rows.map((r) => {
                const isSelected = r.id === selected;
                const isHover = hoverRow === r.id;
                return (
                  <div
                    key={r.id}
                    onMouseEnter={() => setHoverRow(r.id)}
                    onMouseLeave={() => setHoverRow(null)}
                    style={{
                      display: 'grid', gridTemplateColumns: frozenTemplate,
                      height: ROW_H, alignItems: 'center',
                      borderBottom: '1px solid #efebe2',
                      background: isSelected ? 'rgba(154, 106, 20, 0.06)' : isHover ? 'rgba(0,0,0,0.015)' : 'transparent',
                    }}
                  >
                    {/* accent stripe lane */}
                    <div style={{
                      width: ACCENT_W, height: '100%',
                      background: isSelected ? '#9a6a14' : 'transparent',
                    }}></div>
                    <div style={cellStyle({ color: '#8b8676', fontSize: 11, tabular: true })}>{r.id}</div>
                    <div style={cellStyle({ fontSize: 12, fontWeight: 500 })}>{r.co}</div>
                    <div style={cellStyle({ fontSize: 13, fontWeight: 500 })}>{r.title}</div>
                  </div>
                );
              })}
            </div>

            {/* Scroll body */}
            <div
              ref={bodyScrollRef}
              onScroll={onBodyScroll}
              style={{ flex: 1, overflow: 'auto' }}
            >
              <div style={{ minWidth: 'max-content' }}>
                {rows.map((r) => {
                  const isSelected = r.id === selected;
                  const isHover = hoverRow === r.id;
                  const rs = remoteStyle(r.remote);
                  return (
                    <div
                      key={r.id}
                      onMouseEnter={() => setHoverRow(r.id)}
                      onMouseLeave={() => setHoverRow(null)}
                      style={{
                        display: 'grid', gridTemplateColumns: scrollTemplate,
                        height: ROW_H, alignItems: 'center',
                        borderBottom: '1px solid #efebe2',
                        background: isSelected ? 'rgba(154, 106, 20, 0.06)' : isHover ? 'rgba(0,0,0,0.015)' : 'transparent',
                      }}
                    >
                      <div style={cellStyle({ fontSize: 12, color: '#5a5246' })}>{r.loc}</div>

                      {/* Industry — hover reveals excerpt */}
                      <div style={{ ...cellStyle({ fontSize: 12, color: '#3a3a3a' }), position: 'relative', overflow: 'visible' }}>
                        <span style={{
                          borderBottom: '1px dotted #c9c2b0', paddingBottom: 1,
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'inline-block', maxWidth: '100%',
                        }}>{r.industries}</span>
                        {isHover && r.excerpt && (
                          <div style={{
                            position: 'absolute', top: 'calc(100% + 4px)', left: 14, zIndex: 50,
                            width: 360, padding: '12px 14px',
                            background: '#1a1a1a', color: '#fbfaf7', borderRadius: 6,
                            boxShadow: '0 8px 24px rgba(0,0,0,0.25)', fontSize: 12, lineHeight: 1.5,
                            fontFamily: '"Source Serif 4", Georgia, serif', fontStyle: 'italic',
                          }}>
                            <div style={{ fontFamily: '"Inter", sans-serif', fontStyle: 'normal', fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.12em', color: '#a8a39a', marginBottom: 6 }}>
                              Excerpt — why this matched
                            </div>
                            {r.excerpt}
                          </div>
                        )}
                      </div>

                      <div style={{ ...cellStyle({ fontSize: 12, color: matchColor(r.match) }), gap: 5 }}>
                        <span style={{ fontSize: 9 }}>{matchDot(r.match)}</span>
                        <span style={{ textTransform: 'capitalize' }}>{r.match === 'none' ? '—' : r.match}</span>
                      </div>

                      <div style={cellStyle({ fontSize: 12 })}>
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.recruiter}</span>
                        {r.alts > 0 && <span style={{ marginLeft: 6, fontSize: 10, color: '#8b8676', background: '#efebe2', padding: '1px 5px', borderRadius: 3 }}>+{r.alts}</span>}
                      </div>

                      <div style={cellStyle({ fontSize: 12, color: '#3a3a3a', tabular: true, justify: 'flex-end' })}>{r.emp}</div>

                      <div style={cellStyle({})}>
                        <span style={{
                          display: 'inline-block', padding: '2px 8px', borderRadius: 3,
                          fontSize: 10.5, fontWeight: 500,
                          background: rs.bg, color: rs.c,
                        }}>{r.remote}</span>
                      </div>

                      <div style={cellStyle({})}>
                        <span style={{
                          display: 'inline-flex', alignItems: 'center', gap: 5,
                          padding: '3px 8px', borderRadius: 3, fontSize: 11,
                          background: r.status === 'done' ? '#e8efe8' : r.status === 'running' ? '#fff4e0' : r.status === 'error' ? '#fbe5e1' : r.status === 'queued' ? '#e6ecf5' : '#f5f2ec',
                          color: r.status === 'done' ? '#0d6e54' : r.status === 'running' ? '#9a6a14' : r.status === 'error' ? '#9a3a2a' : r.status === 'queued' ? '#3a558a' : '#8b8676',
                        }}>
                          <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'currentColor' }}></span>
                          {r.status}
                        </span>
                      </div>

                      <div style={cellStyle({ fontSize: 11, color: '#8b8676', tabular: true, justify: 'flex-end' })}>{r.time}</div>

                      <div style={{ ...cellStyle({ justify: 'flex-end' }), gap: 4 }}>
                        <span title="Run extraction" style={actionBtn}>▶</span>
                        <span title="Edit URL" style={actionBtn}>✎</span>
                        <span title="Delete" style={actionBtn}>🗑</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Reading pane */}
        {paneOpen && <ReadingPane onClose={() => setPaneOpen(false)} />}
      </div>
    </div>
  );
};

const cellStyle = ({ fontSize = 13, color = '#1a1a1a', fontWeight = 400, tabular = false, justify = 'flex-start' } = {}) => ({
  padding: '0 14px',
  display: 'flex', alignItems: 'center', justifyContent: justify,
  fontSize, color, fontWeight,
  fontVariantNumeric: tabular ? 'tabular-nums' : 'normal',
  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
  height: '100%',
});

const actionBtn = {
  display: 'inline-grid', placeItems: 'center', width: 22, height: 22,
  borderRadius: 4, background: '#fff', border: '1px solid #e0dccf',
  fontSize: 10, color: '#5a5246', cursor: 'pointer',
};

const ReadingPane = ({ onClose }) => (
  <aside style={{
    width: 460, flexShrink: 0,
    borderLeft: '1px solid #e8e4dc', background: '#f7f3ec',
    display: 'flex', flexDirection: 'column', overflow: 'hidden',
  }}>
    <div style={{
      display: 'flex', alignItems: 'center', padding: '14px 22px',
      borderBottom: '1px solid #e6dfd2', gap: 10,
    }}>
      <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.12em', color: '#7a7264' }}>Reading pane</div>
      <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
        <div style={readBtn} title="Copy markdown">📋</div>
        <div style={readBtn} title="Open original">↗</div>
        <div onClick={onClose} style={readBtn} title="Close pane">✕</div>
      </div>
    </div>

    <div style={{ flex: 1, overflow: 'auto', padding: '22px 28px 32px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10, color: '#7a7264', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.12em', flexWrap: 'wrap' }}>
        <span>Transocean</span><span>·</span><span>Houston, TX</span><span>·</span><span>5,400 empl.</span>
        <span style={{
          marginLeft: 4, padding: '2px 7px', background: '#0d6e54', color: '#f7f3ec',
          borderRadius: 999, fontSize: 9, letterSpacing: '0.08em',
        }}>STRONG MATCH</span>
      </div>

      <h1 style={{
        fontFamily: '"Source Serif 4", Georgia, serif', fontWeight: 600,
        fontSize: 28, lineHeight: 1.15, letterSpacing: '-0.02em', margin: '0 0 14px', color: '#1c1813',
      }}>
        Director, Compliance &amp; Risk
      </h1>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 18px', marginBottom: 22, fontSize: 11.5 }}>
        <PaneField label="Industry" value="energy, offshore drilling, regulatory" />
        <PaneField label="Remote" value="Hybrid · Houston" />
        <PaneField label="Recruiter" value="Marisol Vega · +2 alts" />
        <PaneField label="Updated" value="2 minutes ago" />
      </div>

      <div style={{
        padding: '14px 16px', background: '#fff', border: '1px solid #e6dfd2', borderRadius: 6,
        marginBottom: 22,
      }}>
        <div style={{ fontSize: 9.5, textTransform: 'uppercase', letterSpacing: '0.12em', color: '#7a7264', marginBottom: 6 }}>
          Verbatim excerpt — why this matched
        </div>
        <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: 13.5, lineHeight: 1.5, fontStyle: 'italic', color: '#1c1813' }}>
          "Minimum 10 years' experience in offshore drilling, energy, or heavily-regulated industries. Familiarity with BSEE, ABS, and IMO frameworks required."
        </div>
      </div>

      <div style={{ fontFamily: '"Source Serif 4", Georgia, serif', fontSize: 14, lineHeight: 1.6, color: '#2c2820' }}>
        <h3 style={paneH3}>About the role</h3>
        <p style={paneP}>
          Transocean is seeking a Director of Compliance &amp; Risk to lead the Western Hemisphere compliance function from our Houston headquarters. Reporting to the SVP, Legal, this leader will own
          regulatory engagement across BSEE, the U.S. Coast Guard, and Mexican CNH frameworks…
        </p>
        <h3 style={paneH3}>What you'll do</h3>
        <p style={paneP}>· Build the second-line risk framework across drilling assets in the Gulf of Mexico, Brazil, and West Africa.</p>
        <p style={paneP}>· Partner with offshore HSE and asset operations leaders on incident-response readiness…</p>
      </div>
    </div>
  </aside>
);

const readBtn = {
  display: 'inline-grid', placeItems: 'center', width: 26, height: 26,
  background: '#fff', border: '1px solid #e0dccf',
  borderRadius: 5, fontSize: 11, color: '#3a3a3a', cursor: 'pointer',
};

const paneH3 = { fontFamily: 'inherit', fontSize: 15, fontWeight: 600, margin: '0 0 8px', color: '#1c1813' };
const paneP = { margin: '0 0 12px', color: '#3c3528' };

const PaneField = ({ label, value }) => (
  <div>
    <div style={{ fontSize: 9.5, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#7a7264', marginBottom: 3 }}>{label}</div>
    <div style={{ fontSize: 12.5, fontWeight: 500, color: '#1c1813' }}>{value}</div>
  </div>
);

window.Concept1 = Concept1;
