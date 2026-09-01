import os
import sys
import json

# Ensure UTF-8 output encoding for Windows PowerShell / CMD
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

from temporal_engine import analyze_patient

load_dotenv()

URI = os.getenv("CARDIO_NEO4J_URI") or os.getenv("NEO4J_URI")
USERNAME = os.getenv("CARDIO_NEO4J_USERNAME") or os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("CARDIO_NEO4J_PASSWORD") or os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("CARDIO_NEO4J_DATABASE") or os.getenv("NEO4J_DATABASE")

def get_driver():
    try:
        driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))
        driver.verify_connectivity()
        return driver
    except Exception:
        driver = GraphDatabase.driver(URI, auth=("neo4j", PASSWORD))
        driver.verify_connectivity()
        return driver

neo4j_driver = get_driver()

API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_MAIN", "gpt-4.1-mini")

def get_llm_client():
    if not API_KEY:
        return None
    try:
        if ENDPOINT:
            return OpenAI(
                api_key=API_KEY,
                base_url=ENDPOINT
            )
        else:
            return OpenAI(api_key=API_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize OpenAI client: {e}")
        return None

llm_client = get_llm_client()


def get_patient_ids(session):
    result = session.run("""
        MATCH (p:Patient)
        RETURN p.patient_id AS patient_id
        ORDER BY patient_id
    """)
    return [record["patient_id"] for record in result]


def get_patient_data(session, patient_id):
    patient_result = session.run("""
        MATCH (p:Patient {patient_id: $patient_id})
        RETURN
            p.patient_id AS patient_id,
            p.label AS label,
            p.age AS age,
            p.sex AS sex,
            p.t1d_duration AS t1d_duration,
            p.baseline_cvd_context AS baseline_cvd_context,
            p.temporal_pattern AS temporal_pattern
    """, patient_id=patient_id)
    patient = patient_result.single()

    timeline_result = session.run("""
        MATCH (p:Patient {patient_id: $patient_id})
              -[:HAS_VISIT]->
              (v:Visit)
        OPTIONAL MATCH (v)-[:HAS_MEASUREMENT]->(m:Measurement)-[:INSTANCE_OF]->(c:Concept)
        RETURN
            v.visit_id AS visit_id,
            v.date AS date,
            v.smoking_status AS smoking_status,
            v.hypertension_status AS hypertension_status,
            v.dyslipidemia AS dyslipidemia,
            v.known_ascvd AS known_ascvd,
            v.known_cad AS known_cad,
            v.ecg_abnormality AS ecg_abnormality,
            v.cardiovascular_symptoms AS cardiovascular_symptoms,
            v.clinical_action AS clinical_action,
            c.name AS concept,
            m.value AS value,
            m.unit AS unit
        ORDER BY v.date
    """, patient_id=patient_id)

    visits = {}
    for record in timeline_result:
        date = str(record["date"])
        if date not in visits:
            visits[date] = {
                "date": date,
                "visit_id": record["visit_id"],
                "smoking_status": record["smoking_status"],
                "hypertension_status": record["hypertension_status"],
                "dyslipidemia": record["dyslipidemia"],
                "known_ascvd": record["known_ascvd"],
                "known_cad": record["known_cad"],
                "ecg_abnormality": record["ecg_abnormality"],
                "cardiovascular_symptoms": record["cardiovascular_symptoms"],
                "clinical_action": record["clinical_action"]
            }
        if record["concept"]:
            visits[date][record["concept"]] = record["value"]

    timeline = list(visits.values())

    kg_result = session.run("""
        MATCH (c1:Concept)-[r:CLINICAL_RELATIONSHIP]->(c2:Concept)
        RETURN
            c1.name AS source,
            r.relation AS relation,
            c2.name AS target,
            r.evidence_id AS evidence_id,
            r.population AS population,
            r.confidence AS confidence
    """)
    relationships = [dict(record) for record in kg_result]

    evidence_result = session.run("""
        MATCH (e:Evidence)
        RETURN
            e.evidence_id AS evidence_id,
            e.summary AS summary,
            e.citation AS citation,
            e.year AS year,
            e.evidence_strength AS evidence_strength,
            e.population AS population
    """)
    evidence = [dict(record) for record in evidence_result]

    return {
        "patient": dict(patient) if patient else {},
        "timeline": timeline,
        "kg_relationships": relationships,
        "evidence": evidence
    }


def build_reasoning_packet(data):
    temporal = analyze_patient(data["timeline"], data["patient"].get("baseline_cvd_context"))
    return {
        "patient": data["patient"],
        "timeline": data["timeline"],
        "temporal_analysis": temporal,
        "clinical_knowledge": {
            "relationships": data["kg_relationships"],
            "evidence": data["evidence"]
        }
    }


def generate_clinical_output(packet):
    if not llm_client:
        return "Azure OpenAI / OpenAI client is not configured. Displaying packet summary directly."

    prompt = f"""
You are an evidence-grounded clinical reasoning assistant specializing in cardiovascular risk stratification in Type 1 Diabetes (T1D).

You are reviewing a longitudinal synthetic patient for cardiovascular disease (ASCVD, heart failure, hypertension, dyslipidemia) risk forecasting.

Use ONLY the structured temporal findings, clinical rules, and evidence-grounded knowledge graph supplied below.

GUIDELINES:
- Do not invent medical relationships not grounded in the supplied KG and evidence.
- Do not convert risk signals or associations into definitive disease diagnoses unless explicitly established in patient history.
- Distinguish primary prevention vs. secondary prevention contexts.
- For elevated BNP/NT-proBNP, reference ADA recommendation for echocardiography (Stage B heart failure detection).
- Clearly distinguish observed longitudinal measurements from clinical interpretations.

Return your clinical analysis using exactly these structured sections:

CLINICAL SUMMARY
LONGITUDINAL TRAJECTORY
KEY CARDIOVASCULAR FINDINGS
CLINICAL INTERPRETATION & RISK STRATIFICATION
WHAT TO REVIEW & RECOMMENDED INVESTIGATIONS
EVIDENCE GROUNDING

Structured reasoning packet:
{json.dumps(packet, indent=2, default=str)}
"""

    response = llm_client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "You are an evidence-grounded clinical reasoning assistant for cardiovascular complications in Type 1 diabetes."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )
    return response.choices[0].message.content


def main():
    try:
        neo4j_driver.verify_connectivity()
        print("NEO4J CONNECTED")
        with neo4j_driver.session(database=DATABASE) as session:
            patient_ids = get_patient_ids(session)
            print(f"Found {len(patient_ids)} patients for clinical reasoning.")

            for pid in patient_ids:
                print("\n" + "=" * 80)
                print(f"CLINICIAN VIEW — {pid}")
                print("=" * 80)
                data = get_patient_data(session, pid)
                packet = build_reasoning_packet(data)
                output = generate_clinical_output(packet)
                print(output)

    finally:
        neo4j_driver.close()


if __name__ == "__main__":
    main()
