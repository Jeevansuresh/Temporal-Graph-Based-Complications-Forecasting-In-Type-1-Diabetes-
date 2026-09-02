"""Pure CSV reading + reference validation for the Clinical Knowledge Graph.

Mirrors the checks in Retinopathy/validate_kg.py as reusable, testable
functions: every relationship/rule must reference a concept that exists in
nodes.csv, and every evidence_id referenced by a relationship or rule must
exist in evidence_audit.csv. No Neo4j access happens here.
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_csv_rows(root_dir: Path = ROOT_DIR) -> dict[str, list[dict]]:
    return {
        "nodes": read_csv(root_dir / "nodes.csv"),
        "relationships": read_csv(root_dir / "relationships.csv"),
        "rules": read_csv(root_dir / "rules.csv"),
        "evidence": read_csv(root_dir / "evidence.csv"),
        "evidence_audit": read_csv(root_dir / "evidence_audit.csv"),
    }


def _split_evidence_ids(raw: str) -> list[str]:
    return [part for part in (raw or "").split("/") if part]


@dataclass(frozen=True)
class ValidationResult:
    missing_node_refs: list[str] = field(default_factory=list)
    missing_rule_outputs: list[str] = field(default_factory=list)
    missing_relationship_evidence: list[str] = field(default_factory=list)
    missing_rule_evidence: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not any(
            (
                self.missing_node_refs,
                self.missing_rule_outputs,
                self.missing_relationship_evidence,
                self.missing_rule_evidence,
            )
        )


def validate_references(
    nodes: list[dict],
    relationships: list[dict],
    rules: list[dict],
    evidence_audit: list[dict],
) -> ValidationResult:
    names = {row["name"] for row in nodes}
    evidence_ids = {row["claim_id"] for row in evidence_audit}

    missing_node_refs = sorted(
        {
            value
            for row in relationships
            for value in (row["subject"], row["object"])
            if value not in names
        }
    )

    missing_rule_outputs = sorted(
        {
            row["output_concept"]
            for row in rules
            if row["output_concept"] not in names
        }
    )

    missing_relationship_evidence = sorted(
        {
            eid
            for row in relationships
            for eid in _split_evidence_ids(row["evidence_id"])
            if eid not in evidence_ids
        }
    )

    missing_rule_evidence = sorted(
        {
            eid
            for row in rules
            for eid in _split_evidence_ids(row["evidence_id"])
            if eid not in evidence_ids
        }
    )

    return ValidationResult(
        missing_node_refs=missing_node_refs,
        missing_rule_outputs=missing_rule_outputs,
        missing_relationship_evidence=missing_relationship_evidence,
        missing_rule_evidence=missing_rule_evidence,
    )


@dataclass(frozen=True)
class EvidenceCollision:
    id: str
    evidence_csv_source: str
    evidence_csv_year: str
    audit_source: str
    audit_year: str


def _identifier_tokens(*texts: str) -> set[str]:
    """Alphanumeric tokens (>=6 chars) extracted from identifier/url text,
    e.g. "PMID 30705061" and "https://pubmed.ncbi.nlm.nih.gov/30705061/"
    both yield "30705061". Used to compare the underlying source document
    across differently-formatted citation fields, independent of prefix
    text ("PMID", "https://doi.org/", trailing slashes, etc.).
    """
    combined = " ".join(t for t in texts if t)
    return {tok.lower() for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9.\-]{5,}", combined)}


def detect_evidence_id_collisions(
    evidence: list[dict],
    evidence_audit: list[dict],
) -> list[EvidenceCollision]:
    """Flag any id present in BOTH evidence.csv and evidence_audit.csv that
    does not clearly refer to the same underlying source: different
    publication year, or no shared identifier/url token (PMID, DOI, PMC id).

    This does not (and cannot, in general) catch two different specific
    claims drawn from the very same source document under the same id --
    that class of error must still be caught by manual review -- but it
    reliably catches the far more common and more damaging case: an id
    that silently refers to two *different* studies/documents in the two
    files (exactly the class of bug this check was added to prevent; see
    the Milestone 2.5 evidence-integrity correction).
    """
    by_evidence_id = {row["evidence_id"]: row for row in evidence}
    by_claim_id = {row["claim_id"]: row for row in evidence_audit}
    shared_ids = sorted(set(by_evidence_id) & set(by_claim_id))

    collisions = []
    for eid in shared_ids:
        e = by_evidence_id[eid]
        a = by_claim_id[eid]

        same_year = e.get("year") == a.get("year")
        e_tokens = _identifier_tokens(e.get("identifier", ""), e.get("url", ""))
        a_tokens = _identifier_tokens(a.get("identifier", ""), a.get("url", ""))
        shares_identifier = bool(e_tokens & a_tokens)

        if not (same_year and shares_identifier):
            collisions.append(
                EvidenceCollision(
                    id=eid,
                    evidence_csv_source=e.get("citation", ""),
                    evidence_csv_year=e.get("year", ""),
                    audit_source=a.get("source", ""),
                    audit_year=a.get("year", ""),
                )
            )

    return collisions
