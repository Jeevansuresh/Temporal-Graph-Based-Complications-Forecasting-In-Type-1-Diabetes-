# Pediatric T1D Retinopathy TKG Build Pack — V2

This is the audited build specification for the retinopathy module.

The kidney project provides the architectural pattern: a small evidence-backed KG, time-stamped patient observations, temporal trajectory features, explicit rules and explainable output. This retinopathy version makes retinal stage the primary direct temporal trajectory and uses glycemic/BP/kidney/lipid/duration variables as supporting context. The kidney brief explicitly separates the Temporal Patient Graph from the Clinical Knowledge Graph and recommends a transparent baseline before ML.

Before coding:
1. Review evidence_audit.csv.
2. Review relationships.csv and confirm every clinical edge is supported by the cited source.
3. Use synthetic_cases.json for the demo.
4. Give MASTER_CLAUDE_PROMPT.md to Claude Code.

Current evidence base includes ADA Standards of Care 2026, pediatric cohorts, the ADA pediatric position statement, HbA1c variability evidence, and an established DR severity classification.

## Running the demo

**Research/demo prototype only — not for diagnosis or treatment.** Deterministic, rule-based, evidence-cited reasoning over synthetic data; no ML, no calibrated probabilities.

### 1. Set up the environment

```bash
cd Retinopathy
python -m pip install -r requirements.txt
cp .env.example .env   # fill in RETINOPATHY_NEO4J_* with your local Neo4j credentials
```

A Neo4j instance must be reachable at the URI in `.env` (a local Docker container is fine, e.g. `docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/<password> neo4j:2026.07.1`).

### 2. Validate and load the data

```bash
python validate_kg.py                 # must exit 0 before loading anything
python scripts/load_ckg.py            # loads the Clinical Knowledge Graph (nodes/relationships/rules/evidence)
python scripts/load_patients.py       # loads the P001-P005 synthetic Temporal Patient Graph
```

Both loaders are idempotent — safe to rerun.

### 3. Launch the Streamlit app

```bash
streamlit run app/ui/streamlit_app.py
```

Opens at `http://localhost:8501`. Select a patient (P001–P005) to see their context, retinal-stage trajectory, supporting systemic-signal trends, the prominently-displayed risk state (STABLE / WATCH / INCREASING_CONCERN / HIGH_CONCERN / INSUFFICIENT_DATA), and the full evidence-grounded explanation (triggered rules, evidence citations, operational reference standards, and missing-data notes).

The app contains no clinical logic of its own — it only calls `app.reasoning.assess.assess_patient_full()` and reshapes the result for display (`app/ui/view_model.py`, `app/ui/charts.py`).

### 4. Run the tests

```bash
python -m pytest
```
