# BUILD CONTRACT

Build the retinopathy module as a sibling of the kidney module.

Core architecture:
1. Evidence-backed Clinical Knowledge Graph
2. Time-stamped Temporal Patient Graph
3. Temporal feature engine
4. Deterministic reasoning engine
5. Explainable risk state
6. Streamlit demo

Central target:
"Identify emerging or worsening diabetic retinopathy risk/progression from longitudinal pediatric T1D data."

Primary direct trajectory:
Retinal stage

Supporting trajectories:
HbA1c and variability
BP
T1D duration
UACR/eGFR
lipids
age/puberty

V1 must not produce a calibrated probability or claim predictive accuracy.
V1 produces qualitative state:
STABLE / WATCH / INCREASING_CONCERN / HIGH_CONCERN / INSUFFICIENT_DATA

Each clinical KG edge must link to evidence_audit.csv/evidence.csv.
No relationship may be added without provenance.

Do not infer retinopathy from HbA1c/BP/UACR alone.
Observed retinal stage progression is the strongest direct signal.
A missing retinal exam is uncertainty, not evidence of no disease.
Do not model DME in V1.
