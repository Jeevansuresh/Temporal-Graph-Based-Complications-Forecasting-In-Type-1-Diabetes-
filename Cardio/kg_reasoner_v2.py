import os
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

from temporal_engine import (
    calculate_trends,
    determine_worsening_variables
)

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
            return OpenAI(api_key=API_KEY, base_url=ENDPOINT)
        else:
            return OpenAI(api_key=API_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize LLM client: {e}")
        return None

azure_client = get_llm_client()


def get_patient_data(session, patient_id):
    result = session.run("""
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
            m.value AS value
        ORDER BY v.date
    """, patient_id=patient_id)

    timeline = {}
    for record in result:
        date = str(record["date"])
        if date not in timeline:
            timeline[date] = {
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
        concept = record["concept"]
        if concept:
            timeline[date][concept] = record["value"]

    return timeline


def get_kg_relationships(session):
    result = session.run("""
        MATCH (source:Concept)-[r:CLINICAL_RELATIONSHIP]->(target:Concept)
        RETURN
            source.name AS source,
            r.relation AS relationship,
            target.name AS target,
            r.evidence_id AS evidence_id,
            r.confidence AS confidence,
            r.population AS population
    """)
    return [dict(record) for record in result]


def get_rules(session):
    result = session.run("""
        MATCH (r:Rule)
        OPTIONAL MATCH (inp:Concept)-[:INPUT_TO]->(r)
        OPTIONAL MATCH (r)-[:PRODUCES]->(output:Concept)
        OPTIONAL MATCH (r)-[:SUPPORTED_BY]->(e:Evidence)
        RETURN
            r.rule_id AS rule_id,
            r.trigger AS trigger,
            r.logical_condition AS logical_condition,
            r.temporal_requirement AS temporal_requirement,
            inp.name AS input,
            output.name AS output,
            e.evidence_id AS evidence_id,
            e.citation AS evidence,
            e.population AS population
    """)
    return [dict(record) for record in result]


def get_evidence(session):
    result = session.run("""
        MATCH (e:Evidence)
        RETURN
            e.evidence_id AS evidence_id,
            e.citation AS citation,
            e.summary AS summary,
            e.population AS population,
            e.evidence_strength AS evidence_strength
    """)
    return [dict(record) for record in result]


def get_patient_context(session, patient_id):
    result = session.run("""
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
    rec = result.single()
    return dict(rec) if rec else {}


def build_reasoning_packet(patient_context, timeline, trends, worsening_variables, relationships, rules, evidence):
    relevant_relationships = []
    worsening_set = set(worsening_variables)
    
    # Always include baseline cardiovascular concepts
    core_concepts = {"T1D", "T1D_Duration", "Hypertension", "Dyslipidemia", "Albuminuria", "Chronic_Kidney_Disease", "Cardiovascular_Risk", "ASCVD"}

    for rel in relationships:
        if rel["source"] in worsening_set or rel["source"] in core_concepts:
            relevant_relationships.append(rel)

    relevant_rules = []
    for r in rules:
        if r.get("input") in worsening_set or r.get("output") in ["Hypertension", "Albuminuria", "Heart_Failure_Risk", "Secondary_Cardiovascular_Prevention_Context", "Coronary_Investigation_Considered"]:
            relevant_rules.append(r)

    evidence_ids = set()
    for rel in relevant_relationships:
        if rel.get("evidence_id"):
            evidence_ids.add(rel["evidence_id"])
    for r in relevant_rules:
        if r.get("evidence_id"):
            evidence_ids.add(r["evidence_id"])

    relevant_evidence = [item for item in evidence if item["evidence_id"] in evidence_ids]

    return {
        "patient": patient_context,
        "timeline": timeline,
        "trends": trends,
        "worsening_variables": worsening_variables,
        "clinical_relationships": relevant_relationships,
        "clinical_rules": relevant_rules,
        "evidence": relevant_evidence
    }


def ask_azure(reasoning_packet):
    if not azure_client:
        return "Azure OpenAI is not configured."

    prompt = f"""
You are an evidence-grounded clinical reasoning research assistant specializing in cardiovascular disease forecasting in Type 1 Diabetes (T1D).

You are analyzing a SYNTHETIC patient for cardiovascular risk stratification.

CRITICAL INSTRUCTIONS:
- You are NOT providing an unverified diagnostic prescription.
- Use ONLY the information contained in the reasoning packet.
- Do not invent clinical relationships or arbitrary cutoffs not present in the supplied graph/evidence.
- Distinguish primary prevention vs. secondary prevention contexts.
- Check whether clinical rules are satisfied based on the supplied longitudinal measurements before claiming they apply.

REASONING PACKET:
{json.dumps(reasoning_packet, indent=2, default=str)}

Analyze the patient's longitudinal cardiometabolic trajectory and return the analysis in these sections:

TEMPORAL FINDINGS:
Describe the important parameter changes over time (BP, lipids, HbA1c, renal markers, BNP, symptoms).

KG-GROUNDED FINDINGS:
Describe only relationships and pathways explicitly present in the supplied Knowledge Graph.

RULE EVALUATION:
Describe which clinical rules (R001-R007) are satisfied or triggered based strictly on the patient data.

JOINT TEMPORAL PATTERN:
Describe cross-variable interactions (e.g., concurrent BP elevation, dyslipidemia, cardiorenal progression).

EVIDENCE CONTEXT:
Mention the population, guideline source, and strength of the relevant evidence (ADA 2026, AHA/ADA, DCCT-EDIC, ESC).

CLINICAL INTERPRETATION & RISK STRATIFICATION:
Synthesize what the combined longitudinal trajectory indicates regarding cardiovascular risk level.

LIMITATIONS & RECOMMENDED INVESTIGATIONS:
Detail evidence limitations, test cadence recommendations (e.g., echocardiography for abnormal BNP), and lifestyle/clinical considerations.
"""

    response = azure_client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "You are an evidence-grounded clinical reasoning assistant for Type 1 diabetes complications."
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
    target_pid = sys.argv[1] if len(sys.argv) > 1 else "P001"
    try:
        neo4j_driver.verify_connectivity()
        print("NEO4J CONNECTED")
        with neo4j_driver.session(database=DATABASE) as session:
            patient_context = get_patient_context(session, target_pid)
            if not patient_context:
                print(f"Patient {target_pid} not found.")
                return

            timeline = get_patient_data(session, target_pid)
            trends = calculate_trends(timeline)
            worsening = determine_worsening_variables(trends)
            relationships = get_kg_relationships(session)
            rules = get_rules(session)
            evidence = get_evidence(session)

            reasoning_packet = build_reasoning_packet(
                patient_context, timeline, trends, worsening,
                relationships, rules, evidence
            )

            print("\n" + "=" * 80)
            print(f"PATIENT: {target_pid} ({patient_context.get('label')})")
            print("=" * 80)
            print(json.dumps(patient_context, indent=2))

            print("\n" + "=" * 80)
            print("WORSENING VARIABLES")
            print("=" * 80)
            for w in worsening:
                print(f"  - {w}")

            print("\n" + "=" * 80)
            print("REASONING PACKET SUMMARY")
            print("=" * 80)
            print(f"Timeline Visits:          {len(reasoning_packet['timeline'])}")
            print(f"Monitored Trends:         {len(reasoning_packet['trends'])}")
            print(f"Relevant Relationships:   {len(reasoning_packet['clinical_relationships'])}")
            print(f"Relevant Rules:           {len(reasoning_packet['clinical_rules'])}")
            print(f"Relevant Evidence:        {len(reasoning_packet['evidence'])}")

            print("\n" + "=" * 80)
            print("AZURE OPENAI REASONING OUTPUT")
            print("=" * 80)
            answer = ask_azure(reasoning_packet)
            print(answer)

    finally:
        neo4j_driver.close()


if __name__ == "__main__":
    main()
