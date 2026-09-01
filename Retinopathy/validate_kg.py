import csv
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))

from app.graph.csv_validation import detect_evidence_id_collisions


def read(n):
    with open(root / n, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


nodes, rels, rules, ev_audit, ev = map(
    read, ["nodes.csv", "relationships.csv", "rules.csv", "evidence_audit.csv", "evidence.csv"]
)
names = {r["name"] for r in nodes}
eids = {r["claim_id"] for r in ev_audit}
miss_nodes = sorted({x for r in rels for x in (r["subject"], r["object"]) if x not in names})
miss_out = sorted({r["output_concept"] for r in rules if r["output_concept"] not in names})
miss_re = sorted({x for r in rels for x in r["evidence_id"].split("/") if x and x not in eids})
miss_rr = sorted({x for r in rules for x in r["evidence_id"].split("/") if x and x not in eids})
collisions = detect_evidence_id_collisions(ev, ev_audit)

print("Nodes:", len(nodes))
print("Relationships:", len(rels))
print("Rules:", len(rules))
print("Evidence (audit):", len(ev_audit))
print("Evidence (citations):", len(ev))
print("Missing node refs:", miss_nodes)
print("Missing rule outputs:", miss_out)
print("Missing relationship evidence:", miss_re)
print("Missing rule evidence:", miss_rr)
print(
    "Evidence id collisions (evidence.csv vs evidence_audit.csv):",
    [c.id for c in collisions],
)
for c in collisions:
    print(
        f"  {c.id}: evidence.csv={c.evidence_csv_source!r} ({c.evidence_csv_year}) "
        f"vs evidence_audit.csv={c.audit_source!r} ({c.audit_year})"
    )

raise SystemExit(1 if any([miss_nodes, miss_out, miss_re, miss_rr, collisions]) else 0)
