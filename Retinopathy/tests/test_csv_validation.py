from app.graph.csv_validation import (
    detect_evidence_id_collisions,
    load_csv_rows,
    validate_references,
)


def test_real_ckg_csvs_have_no_missing_references():
    rows = load_csv_rows()
    result = validate_references(
        rows["nodes"], rows["relationships"], rows["rules"], rows["evidence_audit"]
    )
    assert result.is_valid
    assert result.missing_node_refs == []
    assert result.missing_rule_outputs == []
    assert result.missing_relationship_evidence == []
    assert result.missing_rule_evidence == []


def test_detects_missing_relationship_node_reference():
    nodes = [{"name": "T1D"}, {"name": "Retinopathy_Risk"}]
    relationships = [
        {
            "subject": "T1D",
            "object": "Nonexistent_Concept",
            "evidence_id": "C001",
        }
    ]
    rules = []
    evidence_audit = [{"claim_id": "C001"}]

    result = validate_references(nodes, relationships, rules, evidence_audit)

    assert not result.is_valid
    assert result.missing_node_refs == ["Nonexistent_Concept"]


def test_detects_missing_rule_output_reference():
    nodes = [{"name": "T1D"}]
    relationships = []
    rules = [
        {
            "rule_id": "RX01",
            "output_concept": "Undefined_Output",
            "evidence_id": "",
        }
    ]
    evidence_audit = []

    result = validate_references(nodes, relationships, rules, evidence_audit)

    assert not result.is_valid
    assert result.missing_rule_outputs == ["Undefined_Output"]


def test_detects_missing_relationship_and_rule_evidence():
    nodes = [{"name": "T1D"}, {"name": "Retinopathy_Risk"}]
    relationships = [
        {
            "subject": "T1D",
            "object": "Retinopathy_Risk",
            "evidence_id": "C999",
        }
    ]
    rules = [
        {
            "rule_id": "RX01",
            "output_concept": "Retinopathy_Risk",
            "evidence_id": "C001/C998",
        }
    ]
    evidence_audit = [{"claim_id": "C001"}]

    result = validate_references(nodes, relationships, rules, evidence_audit)

    assert not result.is_valid
    assert result.missing_relationship_evidence == ["C999"]
    assert result.missing_rule_evidence == ["C998"]


# ---- Evidence-id collision detection (Milestone 2.5) --------------------
#
# evidence.csv and evidence_audit.csv are two independently-curated views of
# the same evidence base and must agree on what each shared id means. A
# real bug of this kind existed (and was fixed) in this repo: evidence.csv's
# "C010" was a 2022 pediatric cohort study while evidence_audit.csv's "C010"
# was the 2019 ICDR severity classification -- two different sources under
# one id. See the Milestone 2.5 report for the full before/after mapping.


def test_real_evidence_files_have_no_id_collisions():
    rows = load_csv_rows()
    collisions = detect_evidence_id_collisions(rows["evidence"], rows["evidence_audit"])
    assert collisions == []


def test_detects_evidence_id_pointing_to_different_sources():
    evidence = [
        {
            "evidence_id": "C010",
            "citation": "Large international pediatric T1D cohort of diabetic retinopathy risk factors",
            "year": "2022",
            "identifier": "PMID 36097824",
            "url": "https://pubmed.ncbi.nlm.nih.gov/36097824/",
        }
    ]
    evidence_audit = [
        {
            "claim_id": "C010",
            "source": "International Clinical Diabetic Retinopathy Disease Severity Scale / ASRS guideline",
            "year": "2019",
            "identifier": "PMC8297841",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC8297841/",
        }
    ]

    collisions = detect_evidence_id_collisions(evidence, evidence_audit)

    assert len(collisions) == 1
    assert collisions[0].id == "C010"


def test_does_not_flag_the_same_source_cited_with_different_wording():
    # Same PMID, same year, slightly different citation phrasing -- must
    # NOT be flagged as a collision.
    evidence = [
        {
            "evidence_id": "C004",
            "citation": "Nordwall et al., VISS Study",
            "year": "2019",
            "identifier": "PMID 30705061",
            "url": "https://pubmed.ncbi.nlm.nih.gov/30705061/",
        }
    ]
    evidence_audit = [
        {
            "claim_id": "C004",
            "source": "Nordwall et al., VISS Study",
            "year": "2019",
            "identifier": "10.2337/dc18-1950",
            "url": "https://pubmed.ncbi.nlm.nih.gov/30705061/",
        }
    ]

    assert detect_evidence_id_collisions(evidence, evidence_audit) == []


def test_ignores_ids_present_in_only_one_file():
    evidence = [{"evidence_id": "C012", "citation": "x", "year": "2026", "identifier": "", "url": ""}]
    evidence_audit = [{"claim_id": "C005", "source": "y", "year": "2018", "identifier": "", "url": ""}]
    assert detect_evidence_id_collisions(evidence, evidence_audit) == []
