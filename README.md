# 🩺 T1D-CareGraph: Temporal Graph-Based Complications Forecasting in Type 1 Diabetes

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Next.js](https://img.shields.io/badge/Next.js-15.1.3-black?logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.0.0-61dafb?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178c6?logo=typescript)](https://www.typescriptlang.org/)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.0+-008CC1?logo=neo4j)](https://neo4j.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?logo=python)](https://www.python.org/)

**T1D-CareGraph** is a state-of-the-art clinical decision support and longitudinal risk forecasting system for Type 1 Diabetes (T1D). By converting multi-year longitudinal patient records, laboratory biomarkers, and therapeutic interventions into **3 organ-specific Clinical Knowledge Graphs (CKGs)** and **1 Temporal Patient Graph (TG)**, T1D-CareGraph predicts complication trajectories across microvascular and macrovascular target organs **12 to 60 months before clinical onset**.

---

## 🔐 Clinical Portal Authentication & Environment Setup

The platform features a secure, HIPAA-compliant login system tailored for endocrinologists and clinical investigators.

### 🔑 Authentication Configuration
Portal access credentials and API configurations are managed securely via environment variables:

```bash
# Configure portal access in your environment or .env file
NEXT_PUBLIC_CLINICAL_EMAIL=doctor@hospital.org
NEXT_PUBLIC_CLINICAL_PASSWORD=your_secure_password
```

- **Portal Access URL:** `http://localhost:3000/login`

---

## 🖼️ Real Knowledge Graph Diagram Previews

Programmatically rendered directly from Neo4j DB instances and extracted graph CSV manifests:

### 1. 🫀 Cardiovascular Knowledge Graph (`Cardio_KG`)
![Cardiovascular Knowledge Graph Real Preview](docs/images/cardio_kg_real.png)

### 2. 🧪 Kidney Knowledge Graph (`Kidney_KG`)
![Kidney Knowledge Graph Real Preview](docs/images/kidney_kg_real.png)

### 3. 👁️ Retinopathy Clinical Knowledge Graph (`Retinopathy_KG`)
![Retinopathy Knowledge Graph Real Preview](docs/images/retinopathy_kg_real.png)

### 4. 👤 Temporal Patient Graph (TG) Patient Profile Timeline
![Temporal Patient Graph Real Preview](docs/images/temporal_patient_graph_real.png)

---

## 🧬 Neo4j Graph Schemas Overview

All graph structures have been extracted via Neo4j Bolt API drivers and defined in detail in:
👉 **[GRAPH_SCHEMAS.md](GRAPH_SCHEMAS.md)**

### Graph Breakdown:

| Graph Identifier | Target Domain | Neo4j Node Labels | Key Relationship Types | Cypher Constraints |
| :--- | :--- | :--- | :--- | :--- |
| **`Kidney_KG`** | Diabetic Nephropathy & CKD Progression | `Concept`, `Evidence`, `Rule`, `Patient`, `Visit`, `Measurement` | `CLINICAL_RELATIONSHIP`, `PRODUCES`, `SUPPORTED_BY`, `INPUT_TO`, `HAS_VISIT`, `HAS_MEASUREMENT`, `INSTANCE_OF` | `c.name`, `r.rule_id`, `e.evidence_id` |
| **`Cardio_KG`** | ASCVD, CAC, & Autonomic Neuropathy | `Concept`, `Evidence`, `Rule`, `Condition`, `Context`, `Measurement`, `Behavior`, `Finding`, `Outcome`, `Process_State`, `Context_State`, `Patient`, `Visit` | `CLINICAL_RELATIONSHIP`, `PRODUCES`, `SUPPORTED_BY`, `INPUT_TO`, `HAS_VISIT`, `HAS_MEASUREMENT`, `INSTANCE_OF`, `NEXT_VISIT` | `c.name`, `c.concept_id`, `r.rule_id`, `e.evidence_id` |
| **`Retinopathy_KG`** | ETDRS Retinal Disease & Macular Edema | `Concept`, `Evidence`, `Rule` | `CLINICAL_RELATIONSHIP`, `PRODUCES`, `SUPPORTED_BY` | `c.name`, `r.rule_id`, `e.evidence_id` |
| **`Temporal_Patient_Graph` (TG)** | Patient Profiles & Time-Series Encounters | `Patient`, `Visit`, `Measurement` | `HAS_VISIT`, `HAS_MEASUREMENT`, `NEXT_VISIT`, `INSTANCE_OF`, `OBSERVED_STATE` | `p.patient_id`, `(v.patient_id, v.date)` |

### Schema Assets:
- **JSON Schema Specification:** [`schemas/graph_schema.json`](schemas/graph_schema.json)
- **TypeScript Type Definitions:** [`frontend/src/types/graph.ts`](frontend/src/types/graph.ts)
- **Live Neo4j Extractor:** [`scratch/extract_schemas.py`](scratch/extract_schemas.py)
- **Real Graph Renderer:** [`generate_real_graph_images.py`](generate_real_graph_images.py)

---

## 🌐 Dashboard Modules

1. **👥 Patient Cohort Explorer (`/patients`)**: Multi-organ patient risk dashboard & cohort filtering.
2. **👁️ Diabetic Retinopathy (`/retinopathy`)**: Microvascular retinal diagnostic reasoning & AI panel.
3. **🫀 Cardiovascular Module (`/cardio`)**: ASCVD, Coronary Calcification, & Autonomic trajectory analyzer.
4. **🧪 Nephropathy & Kidney Module (`/kidney`)**: KDIGO eGFR/UACR renal risk grid & hyperfiltration detection.
5. **🕸️ Knowledge Graph Visualizer (`/knowledge-graph`)**: Dynamic Cytoscape/Vis.js visualization of all 3 CKGs and TG.
6. **📚 Evidence & Guideline Library (`/evidence`)**: ADA 2024, KDIGO 2023, & ETDRS trial provenance library.

---

## 🚀 Setup & Verification

### Run Web Portal
```bash
cd frontend
npm install
npm run dev
```

### Render Real Graph Images
```bash
.\venv\Scripts\python.exe generate_real_graph_images.py
```

### Run Production Build Test
```bash
cd frontend
npm run build
```
