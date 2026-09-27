import json

with open("analyzer/impact_scenarios.json") as f:
    d = json.load(f)

sc = d["scenarios"]
print(len(sc), "scenarios")
for s in sc:
    direct = sum(1 for n in s["blast_radius"] if n["risk"] == "direct")
    downstream = sum(1 for n in s["blast_radius"] if n["risk"] == "downstream")
    print(f"  {s['id']:25} | file={s['task_description']:30} | direct={direct} | downstream={downstream} | checks={len(s['recommended_checks'])}")

# verify all node_ids in blast_radius exist in graph
with open("analyzer/graph.json") as f:
    g = json.load(f)
valid_ids = {n["id"] for n in g["nodes"]}
errors = []
for s in sc:
    for entry in s["blast_radius"]:
        if entry["node_id"] not in valid_ids:
            errors.append(f"  UNKNOWN node_id {entry['node_id']!r} in scenario {s['id']!r}")
if errors:
    print("NODE ID ERRORS:")
    for e in errors:
        print(e)
else:
    print("All blast_radius node_ids match graph.json nodes OK")
