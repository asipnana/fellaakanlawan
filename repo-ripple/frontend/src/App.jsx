import { useState, useRef } from 'react';
import ArchitectureCanvas from './ArchitectureCanvas';
import TaskInput from './TaskInput';
import GuardrailPanel from './GuardrailPanel';

// ── Built-in sample data (bundled at build time — no runtime fetch needed) ────
const SAMPLE_GRAPH = {
  nodes: [
    { id: 'discounts.discounts',            file: 'discounts/discounts.py', type: 'module'   },
    { id: 'discounts.is_valid_code',        file: 'discounts/discounts.py', type: 'function' },
    { id: 'discounts.get_rate',             file: 'discounts/discounts.py', type: 'function' },
    { id: 'discounts.calculate',            file: 'discounts/discounts.py', type: 'function' },
    { id: 'inventory.reserve',              file: 'inventory/reserve.py',   type: 'module'   },
    { id: 'inventory.get_stock',            file: 'inventory/reserve.py',   type: 'function' },
    { id: 'inventory.reserve_item',         file: 'inventory/reserve.py',   type: 'function' },
    { id: 'inventory.release',              file: 'inventory/reserve.py',   type: 'function' },
    { id: 'inventory.set_reservation_timeout', file: 'inventory/reserve.py', type: 'function' },
    { id: 'invoice.generate',               file: 'invoice/generate.py',    type: 'module'   },
    { id: 'invoice.format_invoice',         file: 'invoice/generate.py',    type: 'function' },
    { id: 'invoice.generate_invoice',       file: 'invoice/generate.py',    type: 'function' },
    { id: 'checkout.checkout',              file: 'checkout/checkout.py',   type: 'module'   },
    { id: 'checkout.apply_discount',        file: 'checkout/checkout.py',   type: 'function' },
    { id: 'checkout.get_order_summary',     file: 'checkout/checkout.py',   type: 'function' },
    { id: 'checkout.finalize_order',        file: 'checkout/checkout.py',   type: 'function' },
    { id: 'main',                           file: 'main.py',                type: 'module'   },
    { id: 'main.main',                      file: 'main.py',                type: 'function' },
  ],
  edges: [
    { from: 'checkout.checkout',       to: 'discounts.discounts',       kind: 'imports'  },
    { from: 'checkout.checkout',       to: 'inventory.reserve',         kind: 'imports'  },
    { from: 'checkout.checkout',       to: 'invoice.generate',          kind: 'imports'  },
    { from: 'main',                    to: 'checkout.checkout',         kind: 'imports'  },
    { from: 'checkout.apply_discount', to: 'discounts.is_valid_code',   kind: 'calls'    },
    { from: 'checkout.apply_discount', to: 'discounts.calculate',       kind: 'calls'    },
    { from: 'discounts.calculate',     to: 'discounts.get_rate',        kind: 'calls'    },
    { from: 'invoice.generate_invoice',to: 'invoice.format_invoice',    kind: 'calls'    },
    { from: 'checkout.finalize_order', to: 'inventory.reserve_item',    kind: 'calls'    },
    { from: 'checkout.finalize_order', to: 'checkout.apply_discount',   kind: 'calls'    },
    { from: 'checkout.finalize_order', to: 'invoice.generate_invoice',  kind: 'calls'    },
    { from: 'main.main',               to: 'checkout.get_order_summary',kind: 'calls'    },
    { from: 'main.main',               to: 'checkout.finalize_order',   kind: 'calls'    },
    { from: 'checkout.apply_discount', to: 'invoice.generate_invoice',  kind: 'implicit' },
  ],
};

const SAMPLE_SCENARIOS = {
  scenarios: [
    {
      id: 'modify_discounts',
      task_description: 'discounts/discounts.py',
      blast_radius: [
        { node_id: 'discounts.discounts',      risk: 'direct',     reason: 'Module being modified — owns VALID_CODES table and all discount logic' },
        { node_id: 'discounts.is_valid_code',  risk: 'direct',     reason: 'Function in this file — validates whether a code exists in VALID_CODES' },
        { node_id: 'discounts.get_rate',       risk: 'direct',     reason: 'Function in this file — looks up the decimal rate for a code' },
        { node_id: 'discounts.calculate',      risk: 'direct',     reason: 'Function in this file — applies the rate to an amount and returns the discounted total' },
        { node_id: 'checkout.apply_discount',  risk: 'downstream', reason: 'Calls discounts.is_valid_code and discounts.calculate; any change to validation or arithmetic flows directly into its return value' },
        { node_id: 'checkout.finalize_order',  risk: 'downstream', reason: 'Calls checkout.apply_discount whose result depends on this file; a changed discounted total is passed straight to invoice generation' },
        { node_id: 'invoice.generate_invoice', risk: 'downstream', reason: 'Receives order_data.total produced by checkout.apply_discount (implicit edge); a wrong discount produces a wrong invoice total' },
        { node_id: 'invoice.format_invoice',   risk: 'downstream', reason: 'Called by invoice.generate_invoice to render the total — wrong upstream total propagates into the formatted output' },
        { node_id: 'main.main',                risk: 'downstream', reason: 'Drives finalize_order end-to-end; the final logged invoice reflects any change in discount arithmetic' },
      ],
      recommended_checks: [
        'Unit-test discounts.calculate for every entry in VALID_CODES and assert the rounded result matches expected arithmetic',
        'Verify discounts.is_valid_code returns False for an unrecognised code and that checkout.apply_discount returns the original total unchanged',
        'Confirm discounts.get_rate returns 0 for unknown codes so calculate never produces a negative total',
        'Run main.py end-to-end with SAVE10, SAVE20, and HALF and assert the printed invoice total is correct for each',
      ],
    },
    {
      id: 'modify_inventory',
      task_description: 'inventory/reserve.py',
      blast_radius: [
        { node_id: 'inventory.reserve',                file: 'inventory/reserve.py', risk: 'direct',     reason: 'Module being modified — owns _stock state and all reservation logic' },
        { node_id: 'inventory.get_stock',              risk: 'direct',     reason: 'Function in this file — reads current on-hand quantity from _stock' },
        { node_id: 'inventory.reserve_item',           risk: 'direct',     reason: 'Function in this file — decrements _stock and guards against over-reservation' },
        { node_id: 'inventory.release',                risk: 'direct',     reason: 'Function in this file — increments _stock to free a held reservation' },
        { node_id: 'inventory.set_reservation_timeout',risk: 'direct',     reason: 'Function in this file — configures the global auto-release timeout' },
        { node_id: 'checkout.finalize_order',          risk: 'downstream', reason: 'Calls inventory.reserve_item for each cart item; a change to reservation logic directly affects whether finalize_order succeeds' },
      ],
      recommended_checks: [
        'Test inventory.reserve_item with sufficient stock, insufficient stock, and exactly-zero stock to confirm correct True/False return and _stock mutation',
        'Verify inventory.release correctly restores stock and that a reserve followed by release leaves _stock unchanged',
        'Confirm checkout.finalize_order still completes a full order when stock is sufficient, and handles False from reserve_item gracefully',
        'Check set_reservation_timeout persists the value and does not affect _stock or reservation logic',
      ],
    },
    {
      id: 'modify_invoice',
      task_description: 'invoice/generate.py',
      blast_radius: [
        { node_id: 'invoice.generate',         risk: 'direct',     reason: 'Module being modified — owns _invoice_counter and all invoice creation logic' },
        { node_id: 'invoice.format_invoice',   risk: 'direct',     reason: 'Function in this file — renders the invoice dict into a human-readable string' },
        { node_id: 'invoice.generate_invoice', risk: 'direct',     reason: 'Function in this file — increments the counter, builds the invoice dict, and calls format_invoice' },
        { node_id: 'checkout.finalize_order',  risk: 'downstream', reason: "Calls invoice.generate_invoice and reads invoice['id'] from the returned dict; a change to the dict shape or counter logic breaks this caller" },
        { node_id: 'main.main',                risk: 'downstream', reason: 'Receives the invoice dict from finalize_order and logs it; a changed dict shape or missing keys surface here at runtime' },
      ],
      recommended_checks: [
        'Assert invoice.generate_invoice increments _invoice_counter on each call and that the returned dict contains id, items, and total keys',
        'Test format_invoice with a known invoice dict and assert the output string contains the correct id, item lines, and formatted total',
        "Verify checkout.finalize_order still reads invoice['id'] correctly after any schema change to the returned dict",
        'Run main.py and confirm the final log line prints the full invoice dict without KeyError',
      ],
    },
    {
      id: 'modify_checkout',
      task_description: 'checkout/checkout.py',
      blast_radius: [
        { node_id: 'checkout.checkout',         risk: 'direct',     reason: 'Module being modified — imports from discounts, inventory, and invoice; owns the full order-finalisation flow' },
        { node_id: 'checkout.apply_discount',   risk: 'direct',     reason: 'Function in this file — validates the code and returns the discounted total' },
        { node_id: 'checkout.get_order_summary',risk: 'direct',     reason: 'Function in this file — returns a summary dict read by main.main' },
        { node_id: 'checkout.finalize_order',   risk: 'direct',     reason: 'Function in this file — orchestrates reserve, apply_discount, and generate_invoice' },
        { node_id: 'discounts.discounts',       risk: 'downstream', reason: 'Imported by checkout.checkout (imports edge); changes to the import or usage of discounts symbols affect this module' },
        { node_id: 'discounts.is_valid_code',   risk: 'downstream', reason: 'Called by checkout.apply_discount (calls edge); any change to how apply_discount invokes or interprets this function propagates here' },
        { node_id: 'discounts.calculate',       risk: 'downstream', reason: 'Called by checkout.apply_discount (calls edge); changes to argument passing or result handling affect the discount calculation path' },
        { node_id: 'inventory.reserve',         risk: 'downstream', reason: 'Imported by checkout.checkout (imports edge); changes to how checkout uses the reserve module affect stock state' },
        { node_id: 'inventory.reserve_item',    risk: 'downstream', reason: 'Called by checkout.finalize_order (calls edge); changes to the call site affect which items get reserved' },
        { node_id: 'invoice.generate',          risk: 'downstream', reason: 'Imported by checkout.checkout (imports edge); changes to how checkout constructs or passes order_data affect invoice correctness' },
        { node_id: 'invoice.generate_invoice',  risk: 'downstream', reason: 'Called by checkout.finalize_order (calls edge) and implicitly receives the discounted total via checkout.apply_discount (implicit edge)' },
        { node_id: 'main.main',                 risk: 'downstream', reason: 'Calls checkout.get_order_summary and checkout.finalize_order (calls edges); any signature or return-value change in this file breaks the entry point' },
      ],
      recommended_checks: [
        'Test finalize_order end-to-end with a valid code and assert stock is decremented, the total is discounted, and the returned invoice dict is correct',
        'Verify apply_discount returns cart_total unchanged for an invalid code and the correct discounted value for each valid code',
        'Confirm get_order_summary always returns a dict with at least items, subtotal, and status keys',
        'Run main.py and assert no import errors, no KeyError on invoice fields, and the printed output matches expected values',
      ],
    },
    {
      id: 'modify_main',
      task_description: 'main.py',
      blast_radius: [
        { node_id: 'main',                      risk: 'direct',     reason: 'Module being modified — entry point that imports and drives the entire order flow' },
        { node_id: 'main.main',                 risk: 'direct',     reason: 'Function in this file — calls get_order_summary and finalize_order and logs results' },
        { node_id: 'checkout.checkout',         risk: 'downstream', reason: 'Imported by main (imports edge); any change to which symbols are imported or how they are called affects checkout behaviour' },
        { node_id: 'checkout.get_order_summary',risk: 'downstream', reason: 'Called by main.main (calls edge); changes to the call site or how its return value is used surface here' },
        { node_id: 'checkout.finalize_order',   risk: 'downstream', reason: 'Called by main.main (calls edge) with a hardcoded cart and code; changes to arguments passed here affect the full downstream order and invoice flow' },
      ],
      recommended_checks: [
        'Run main.py directly and assert exit code 0 with no unhandled exceptions',
        'Verify the cart dict and discount code passed to finalize_order match the items present in inventory._stock',
        'Confirm the logged invoice output contains the expected id, items, and total fields',
        'Check that changes to main.py do not alter the public API of any imported module (main should only be a consumer, not a mutator)',
      ],
    },
  ],
};

// ── Palette (shared across landing + app shell) ───────────────────────────────
const C = {
  bg:       '#0B2545',
  panel:    '#123A63',
  border:   '#3E6E96',
  text:     '#F4F7FA',
  muted:    '#8ECAE6',
  dimmed:   '#5A7FA0',
  accent:   '#2E86C1',
  fontSans: '"IBM Plex Sans", sans-serif',
  fontMono: '"IBM Plex Mono", monospace',
};

// ── Layout constants ──────────────────────────────────────────────────────────
const SIDEBAR_WIDTH = 320;

// ── Shared shell styles ───────────────────────────────────────────────────────
const appStyle = {
  display: 'flex', flexDirection: 'column',
  width: '100vw', height: '100vh',
  overflow: 'hidden', background: C.bg,
};

const headerStyle = {
  flexShrink: 0,
  padding: '12px 20px',
  background: C.bg,
  borderBottom: `1px solid ${C.border}`,
  display: 'flex', alignItems: 'center', gap: '12px',
};

const logoStyle = {
  color: C.text, fontFamily: C.fontMono,
  fontSize: '15px', fontWeight: 600,
  letterSpacing: '0.05em', margin: 0,
};

const taglineStyle = {
  color: C.muted, fontFamily: C.fontSans,
  fontSize: '12px', margin: 0,
};

// ── Landing screen styles ─────────────────────────────────────────────────────
const landingWrapStyle = {
  flex: 1, display: 'flex',
  alignItems: 'center', justifyContent: 'center',
  padding: '40px 20px',
};

const cardStyle = {
  width: '100%', maxWidth: '560px',
  background: C.panel,
  border: `1px solid ${C.border}`,
  borderRadius: '4px',
  padding: '36px 32px',
};

const cardHeadStyle = {
  margin: '0 0 8px',
  color: C.text, fontFamily: C.fontMono,
  fontSize: '18px', fontWeight: 600,
};

const cardSubStyle = {
  margin: '0 0 32px',
  color: C.muted, fontFamily: C.fontSans,
  fontSize: '13px', lineHeight: 1.6,
};

const dividerStyle = {
  border: 'none', borderTop: `1px solid ${C.border}`,
  margin: '24px 0', opacity: 0.5,
};

const primaryBtnStyle = {
  display: 'block', width: '100%',
  padding: '11px 16px',
  background: C.accent,
  color: C.text, fontFamily: C.fontMono,
  fontSize: '13px', fontWeight: 600,
  border: 'none', borderRadius: '3px',
  cursor: 'pointer', textAlign: 'left',
  letterSpacing: '0.02em',
};

const primaryBtnSubStyle = {
  display: 'block', marginTop: '4px',
  fontFamily: C.fontSans, fontSize: '11px',
  fontWeight: 400, opacity: 0.85,
};

const sectionLabelStyle = {
  display: 'block', marginBottom: '12px',
  color: C.muted, fontFamily: C.fontMono,
  fontSize: '11px', letterSpacing: '0.08em',
  textTransform: 'uppercase',
};

const uploadRowStyle = {
  display: 'grid', gridTemplateColumns: '1fr 1fr',
  gap: '10px', marginBottom: '14px',
};

const fileInputWrapStyle = {
  position: 'relative',
  border: `1px dashed ${C.border}`,
  borderRadius: '3px',
  padding: '12px',
  cursor: 'pointer',
  background: C.bg,
};

const fileInputLabelStyle = {
  display: 'block',
  color: C.muted, fontFamily: C.fontMono,
  fontSize: '11px', marginBottom: '4px',
  pointerEvents: 'none',
};

const fileInputNameStyle = {
  color: C.text, fontFamily: C.fontSans,
  fontSize: '11px', wordBreak: 'break-all',
};

const hiddenInputStyle = {
  position: 'absolute', inset: 0,
  opacity: 0, cursor: 'pointer', width: '100%',
};

const uploadBtnStyle = {
  display: 'block', width: '100%',
  padding: '10px 16px',
  background: 'transparent',
  color: C.muted, fontFamily: C.fontMono,
  fontSize: '12px',
  border: `1px solid ${C.border}`,
  borderRadius: '3px',
  cursor: 'pointer', textAlign: 'left',
};

const errorTextStyle = {
  marginTop: '12px',
  color: '#E63946', fontFamily: C.fontSans,
  fontSize: '12px',
};

// ── App-shell styles ──────────────────────────────────────────────────────────
const bodyStyle      = { flex: 1, display: 'flex', overflow: 'hidden' };
const canvasAreaStyle = { flex: 1, overflow: 'hidden', position: 'relative' };
const sidebarStyle   = {
  width: `${SIDEBAR_WIDTH}px`, flexShrink: 0,
  display: 'flex', flexDirection: 'column',
  overflow: 'hidden', borderLeft: `1px solid ${C.border}`,
};

// ── App ───────────────────────────────────────────────────────────────────────
export default function App() {
  // 'landing' | 'app'
  const [mode, setMode] = useState('landing');
  const [graphData, setGraphData]       = useState(null);
  const [scenarioData, setScenarioData] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState(null);

  // File upload state
  const [graphFile,    setGraphFile]    = useState(null);
  const [scenarioFile, setScenarioFile] = useState(null);
  const [uploadError,  setUploadError]  = useState('');

  const graphInputRef    = useRef(null);
  const scenarioInputRef = useRef(null);

  // ── Landing handlers ────────────────────────────────────────────────────────

  function loadSampleDemo() {
    setGraphData(SAMPLE_GRAPH);
    setScenarioData(SAMPLE_SCENARIOS);
    setMode('app');
  }

  function handleGraphFileChange(e) {
    setGraphFile(e.target.files[0] || null);
    setUploadError('');
  }

  function handleScenarioFileChange(e) {
    setScenarioFile(e.target.files[0] || null);
    setUploadError('');
  }

  function loadUploadedFiles() {
    if (!graphFile || !scenarioFile) {
      setUploadError('Please select both graph.json and impact_scenarios.json before loading.');
      return;
    }
    const readJSON = (file) =>
      new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
          try { resolve(JSON.parse(e.target.result)); }
          catch { reject(new Error(`${file.name} is not valid JSON.`)); }
        };
        reader.onerror = () => reject(new Error(`Could not read ${file.name}.`));
        reader.readAsText(file);
      });

    Promise.all([readJSON(graphFile), readJSON(scenarioFile)])
      .then(([graph, scenarios]) => {
        if (!graph.nodes || !graph.edges)
          throw new Error('graph.json is missing "nodes" or "edges" fields.');
        if (!scenarios.scenarios)
          throw new Error('impact_scenarios.json is missing a "scenarios" field.');
        setGraphData(graph);
        setScenarioData(scenarios);
        setMode('app');
      })
      .catch((err) => setUploadError(err.message));
  }

  // ── Derived app-shell values ────────────────────────────────────────────────
  const blastRadius =
    selectedScenario ? (selectedScenario.blast_radius ?? []) : undefined;
  const recommendedChecks = selectedScenario?.recommended_checks ?? [];

  // ── Shared header ───────────────────────────────────────────────────────────
  const header = (
    <header style={headerStyle}>
      <h1 style={logoStyle}>Repo Ripple</h1>
      <span style={taglineStyle}>Understand any codebase, change anything safely.</span>
      {mode === 'app' && (
        <button
          onClick={() => { setMode('landing'); setSelectedScenario(null); setGraphData(null); setScenarioData(null); }}
          style={{
            marginLeft: 'auto', padding: '5px 12px',
            background: 'transparent', color: C.dimmed,
            fontFamily: C.fontMono, fontSize: '11px',
            border: `1px solid ${C.border}`, borderRadius: '2px',
            cursor: 'pointer',
          }}
        >
          ← Change repo
        </button>
      )}
    </header>
  );

  // ── Landing screen ──────────────────────────────────────────────────────────
  if (mode === 'landing') {
    return (
      <div style={appStyle}>
        {header}
        <div style={landingWrapStyle}>
          <div style={cardStyle}>

            <h2 style={cardHeadStyle}>Choose your data source</h2>
            <p style={cardSubStyle}>
              Run both Bob passes first to generate <code style={{ fontFamily: C.fontMono, fontSize: '12px' }}>graph.json</code> and{' '}
              <code style={{ fontFamily: C.fontMono, fontSize: '12px' }}>impact_scenarios.json</code>, then upload them — or
              load the built-in sample repo to see the demo instantly.
            </p>

            {/* Option A — Sample demo */}
            <button style={primaryBtnStyle} onClick={loadSampleDemo}>
              ⚡ Load Sample Demo Repo
              <span style={primaryBtnSubStyle}>
                Instantly loads a pre-analysed e-commerce repo — no files needed
              </span>
            </button>

            <hr style={dividerStyle} />

            {/* Option B — Upload own files */}
            <span style={sectionLabelStyle}>Upload your own analysis files</span>

            <div style={uploadRowStyle}>
              {/* graph.json picker */}
              <div style={fileInputWrapStyle}>
                <span style={fileInputLabelStyle}>graph.json</span>
                <span style={fileInputNameStyle}>
                  {graphFile ? graphFile.name : 'Click to select…'}
                </span>
                <input
                  ref={graphInputRef}
                  type="file"
                  accept=".json,application/json"
                  style={hiddenInputStyle}
                  onChange={handleGraphFileChange}
                />
              </div>

              {/* impact_scenarios.json picker */}
              <div style={fileInputWrapStyle}>
                <span style={fileInputLabelStyle}>impact_scenarios.json</span>
                <span style={fileInputNameStyle}>
                  {scenarioFile ? scenarioFile.name : 'Click to select…'}
                </span>
                <input
                  ref={scenarioInputRef}
                  type="file"
                  accept=".json,application/json"
                  style={hiddenInputStyle}
                  onChange={handleScenarioFileChange}
                />
              </div>
            </div>

            <button
              style={{
                ...uploadBtnStyle,
                ...(graphFile && scenarioFile
                  ? { color: C.text, borderColor: C.muted }
                  : {}),
              }}
              onClick={loadUploadedFiles}
            >
              Load uploaded files →
            </button>

            {uploadError && (
              <p style={errorTextStyle}>{uploadError}</p>
            )}

          </div>
        </div>
      </div>
    );
  }

  // ── App shell ───────────────────────────────────────────────────────────────
  return (
    <div style={appStyle}>
      {header}
      <div style={bodyStyle}>
        <div style={canvasAreaStyle}>
          <ArchitectureCanvas
            blastRadius={blastRadius || null}
            graphData={graphData}
          />
        </div>
        <aside style={sidebarStyle}>
          <TaskInput
            onScenarioSelected={setSelectedScenario}
            selectedScenario={selectedScenario}
            scenarioData={scenarioData}
          />
          <GuardrailPanel
            blastRadius={blastRadius}
            recommendedChecks={recommendedChecks}
          />
        </aside>
      </div>
    </div>
  );
}
