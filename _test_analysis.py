"""
Test run_analysis.py dengan mock Bob.
Node ID format: 2-level (checkout.apply_discount) sesuai spec section 4.
Mock responses mencerminkan isi sample-repo_PersonA yang sesungguhnya.
"""
import sys, json, pathlib, tempfile
sys.path.insert(0, 'analyzer')
import run_analysis as ra

RESPONSES = {
    'main.py': json.dumps({
        'functions_defined': ['main'],
        'functions_called': [
            {'caller': 'main', 'callee': 'finalize_order'},
            {'caller': 'main', 'callee': 'get_order_summary'},
        ],
        'imports': [
            'from checkout.checkout import finalize_order, get_order_summary'
        ],
        'implicit_data_consumers': []
    }),
    'checkout/__init__.py': json.dumps({
        'functions_defined': [], 'functions_called': [], 'imports': [], 'implicit_data_consumers': []
    }),
    'checkout/checkout.py': json.dumps({
        'functions_defined': ['apply_discount', 'finalize_order', 'get_order_summary'],
        'functions_called': [
            # Bob reports aliases as callee names — the bug being fixed
            {'caller': 'apply_discount',  'callee': 'is_valid_code'},
            {'caller': 'apply_discount',  'callee': 'discounts_calculate'},   # alias
            {'caller': 'finalize_order',  'callee': 'inventory_reserve'},     # alias
            {'caller': 'finalize_order',  'callee': 'apply_discount'},
            {'caller': 'finalize_order',  'callee': 'invoice_generate'},      # alias
        ],
        'imports': [
            'from discounts.discounts import calculate as discounts_calculate, is_valid_code',
            'from inventory.reserve import reserve as inventory_reserve, RESERVATION_TIMEOUT_SECONDS',
            'from invoice.generate import generate as invoice_generate'
        ],
        'implicit_data_consumers': ['finalize_order']
    }),
    'discounts/__init__.py': json.dumps({
        'functions_defined': [], 'functions_called': [], 'imports': [], 'implicit_data_consumers': []
    }),
    'discounts/discounts.py': json.dumps({
        'functions_defined': ['calculate', 'is_valid_code', 'get_rate'],
        'functions_called': [], 'imports': [], 'implicit_data_consumers': []
    }),
    'inventory/__init__.py': json.dumps({
        'functions_defined': [], 'functions_called': [], 'imports': [], 'implicit_data_consumers': []
    }),
    'inventory/reserve.py': json.dumps({
        'functions_defined': ['reserve', 'release', 'get_stock', 'set_reservation_timeout'],
        'functions_called': [], 'imports': [], 'implicit_data_consumers': []
    }),
    'invoice/__init__.py': json.dumps({
        'functions_defined': [], 'functions_called': [], 'imports': [], 'implicit_data_consumers': []
    }),
    'invoice/generate.py': json.dumps({
        'functions_defined': ['generate', 'format_invoice'],
        'functions_called': [], 'imports': [], 'implicit_data_consumers': []
    }),
}
CROSS = json.dumps([
    {'from': 'checkout.apply_discount', 'to': 'invoice.generate', 'kind': 'implicit'},
    {'from': 'checkout.finalize_order', 'to': 'invoice.generate', 'kind': 'implicit'},
])

call_count = [0]
cross_call_count = [0]

def mock_bob(prompt):
    call_count[0] += 1
    # Cross-file pass prompt contains this unique header line from the
    # _PROMPT_RESOLVE_CROSS_FILE template — per-file prompts never contain it.
    # Do NOT use file path substrings: cross-file JSON body contains every
    # file path as a field value, causing false matches.
    if "Below is a JSON summary of every file in the repo:" in prompt:
        cross_call_count[0] += 1
        return CROSS
    # Per-file pass: match on "File path: <key>" which is unique to each file prompt
    for file_key, resp in RESPONSES.items():
        if f"File path: {file_key}" in prompt:
            return resp
    # Fallback — should not happen in a correct test
    raise AssertionError(f"mock_bob: unrecognised prompt (first 120 chars): {prompt[:120]!r}")

ra._call_bob_agent = mock_bob

repo_path = pathlib.Path('sample-repo').resolve()
with tempfile.TemporaryDirectory() as tmpdir:
    out = pathlib.Path(tmpdir) / 'graph.json'
    ra.run_analysis(repo_path, out)
    data = json.loads(out.read_text())

failures = []

# --- Schema ---
for n in data['nodes']:
    if not ('id' in n and 'file' in n and 'type' in n):
        failures.append('BAD NODE SCHEMA: ' + str(n))
for e in data['edges']:
    if not ('from' in e and 'to' in e and 'kind' in e):
        failures.append('BAD EDGE SCHEMA: ' + str(e))

# --- Forward slashes only in file paths ---
for n in data['nodes']:
    if '\\' in n['file']:
        failures.append('BACKSLASH IN FILE PATH: ' + str(n))

# --- 2-level function node IDs (spec section 4) ---
for n in data['nodes']:
    parts = n['id'].split('.')
    if n['type'] == 'function' and len(parts) != 2:
        failures.append('NOT 2-LEVEL FUNCTION NODE: ' + n['id'])
    if n['type'] == 'module' and len(parts) != 1:
        failures.append('NOT 1-LEVEL MODULE NODE: ' + n['id'])

# --- Empty __init__-only modules must NOT appear as module nodes ---
node_map = {n['id']: n for n in data['nodes']}
empty_module_ids = ['discounts', 'inventory', 'invoice', 'checkout']
# These all have substantive sibling files so they SHOULD appear — but
# their "file" field must point to the substantive file, not __init__.py
for mid in empty_module_ids:
    if mid not in node_map:
        failures.append('MODULE NODE MISSING: ' + mid)
    elif node_map[mid]['file'].endswith('__init__.py'):
        failures.append(
            'MODULE NODE FILE POINTS TO __init__.py (should be substantive file): '
            + mid + ' -> ' + node_map[mid]['file']
        )

# --- checkout module specifically must point to checkout/checkout.py ---
if 'checkout' in node_map:
    expected = 'checkout/checkout.py'
    actual = node_map['checkout']['file']
    if actual != expected:
        failures.append(
            'checkout module file wrong: expected %s got %s' % (expected, actual)
        )

# --- Required nodes from spec section 4 ---
node_ids = {n['id'] for n in data['nodes']}
required_nodes = [
    'checkout.apply_discount',
    'checkout.finalize_order',
    'discounts.calculate',
    'discounts.is_valid_code',
    'inventory.reserve',
    'invoice.generate',
]
for nid in required_nodes:
    if nid not in node_ids:
        failures.append('MISSING REQUIRED NODE: ' + nid)

# --- Key edges from spec ---
edge_tuples = {(e['from'], e['to'], e['kind']) for e in data['edges']}

# spec section 4: checkout.apply_discount -> invoice.generate
if ('checkout.apply_discount', 'invoice.generate', 'calls') not in edge_tuples and \
   ('checkout.apply_discount', 'invoice.generate', 'implicit') not in edge_tuples and \
   ('checkout.finalize_order', 'invoice.generate', 'calls') not in edge_tuples:
    failures.append('MISSING SPEC EDGE: checkout.* -> invoice.generate')

required_call_edges = [
    ('checkout.apply_discount', 'discounts.calculate', 'calls'),
    ('checkout.apply_discount', 'discounts.is_valid_code', 'calls'),
    ('checkout.finalize_order', 'inventory.reserve', 'calls'),
    ('checkout.finalize_order', 'invoice.generate', 'calls'),
]
for tup in required_call_edges:
    if tup not in edge_tuples:
        failures.append('MISSING CALL EDGE: ' + str(tup))

# --- Cross-file (implicit) pass was actually called exactly once ---
if cross_call_count[0] != 1:
    failures.append(f'CROSS-FILE BOB PASS called {cross_call_count[0]} times, expected 1')

# --- Implicit edge for genuinely new (from,to) pair is kept ---
# checkout.apply_discount -> invoice.generate has no explicit calls/imports edge,
# so it should survive the filter.
if ('checkout.apply_discount', 'invoice.generate', 'implicit') not in edge_tuples:
    failures.append('MISSING IMPLICIT EDGE: checkout.apply_discount -> invoice.generate (implicit)')

# --- Duplicate-suppression: checkout.finalize_order -> invoice.generate (calls)
# already exists as an explicit edge, so the implicit variant from Bob must be DROPPED.
if ('checkout.finalize_order', 'invoice.generate', 'implicit') in edge_tuples:
    failures.append('DUPLICATE IMPLICIT EDGE NOT DROPPED: checkout.finalize_order -> invoice.generate')
if ('checkout.finalize_order', 'invoice.generate', 'calls') not in edge_tuples:
    failures.append('EXPLICIT EDGE MISSING: checkout.finalize_order -> invoice.generate (calls)')

if failures:
    print()
    print('FAILURES:')
    for f in failures:
        print('  FAIL:', f)
    sys.exit(1)

print()
print('ALL ASSERTIONS PASSED')
print('Bob calls  :', call_count[0], '(per-file: %d, cross-file: %d)' % (call_count[0] - cross_call_count[0], cross_call_count[0]))
nodes_fn  = [n for n in data['nodes'] if n['type'] == 'function']
nodes_mod = [n for n in data['nodes'] if n['type'] == 'module']
print('Nodes     :', len(data['nodes']), '(%d modules, %d functions)' % (len(nodes_mod), len(nodes_fn)))
print('Edges     :', len(data['edges']))
kinds = {}
for e in data['edges']:
    kinds[e['kind']] = kinds.get(e['kind'], 0) + 1
print('Edge kinds:', kinds)
print()
print('Nodes (sorted):')
for n in sorted(data['nodes'], key=lambda x: x['id']):
    print('  %-10s %-35s %s' % (n['type'], n['id'], n['file']))
print()
print('Edges (sorted):')
for e in sorted(data['edges'], key=lambda x: (x['from'], x['to'])):
    print('  [%-8s]  %-35s ->  %s' % (e['kind'], e['from'], e['to']))
