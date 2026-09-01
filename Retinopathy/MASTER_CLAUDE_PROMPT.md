You are Claude Code building a research prototype.

Read ALL project files before coding:
- BUILD_CONTRACT.md
- evidence_audit.csv
- nodes.csv
- relationships.csv
- rules.csv
- synthetic_cases.json

PROJECT:
Evidence-Grounded Temporal Knowledge Graph for Early Diabetic Retinopathy Progression Risk in Pediatric Type 1 Diabetes.

ARCHITECTURE:
Temporal Patient Graph + Clinical Knowledge Graph + deterministic temporal reasoning engine + explainable Streamlit dashboard.

HARD CLINICAL SAFETY/RESEARCH CONSTRAINTS:
- No ML in V1.
- No calibrated probabilities.
- No diagnostic or autonomous treatment claims.
- No invented medical relationships.
- Every clinical relationship must have evidence_id and trace to evidence_audit.csv.
- Preserve evidence population/context.
- Treat risk-factor edges as associations unless the source clearly supports causality.
- Do not infer DR solely from HbA1c, BP, UACR, lipids or duration.
- Direct retinal stage progression is the strongest direct observation.
- Missing retinal data should produce uncertainty.
- Do not model diabetic macular edema in V1.
- Pediatric BP must use age/sex/height context; don't hard-code adult thresholds.

CLINICAL STAGE:
0 No DR
1 Mild NPDR
2 Moderate NPDR
3 Severe NPDR
4 PDR

BUILD ORDER:
1. Repository structure
2. Neo4j graph import and schema
3. Observation/patient data model
4. Temporal feature engine
5. Retinal-stage transition engine
6. Rule engine
7. Evidence/provenance retrieval
8. Risk-state aggregation
9. Explanation engine
10. Streamlit dashboard
11. Automated tests
12. README/run instructions

SUGGESTED STRUCTURE:
retinopathy-tkg/
  data/
  app/
    graph/
    temporal/
    reasoning/
    extraction/
    ui/
  tests/
  scripts/

DEMO:
Use synthetic_cases.json initially. The user should be able to select P001-P005 and see:
- summary
- retinal stage timeline
- HbA1c/BP/UACR/eGFR/LDL trajectories
- risk state
- triggered rules
- reasoning path
- evidence citations
- uncertainty/data quality
- screening context

Use Neo4j via Docker if available.
Use Python + neo4j-driver.
Use Streamlit for V1 dashboard.
Use Plotly for timelines if convenient.
Use .env for NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD.

Create the code, tests, and README. Do not stop after generating a plan: implement the working V1.


## PRE-IMPORT VALIDATION
Before importing into Neo4j, run `python validate_kg.py`. Do not import if validation fails. Report counts and validation result.
