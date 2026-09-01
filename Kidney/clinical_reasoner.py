import os
import json

from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

from temporal_engine import analyze_patient


load_dotenv()


neo4j_driver = GraphDatabase.driver(
    os.getenv("KIDNEY_NEO4J_URI"),
    auth=(
        os.getenv("KIDNEY_NEO4J_USERNAME"),
        os.getenv("KIDNEY_NEO4J_PASSWORD")
    )
)


azure_client = OpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=os.getenv("AZURE_OPENAI_ENDPOINT")
)

DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_DEPLOYMENT_MAIN"
)


def get_patient_ids(session):

    result = session.run("""
        MATCH (p:Patient)
        RETURN p.patient_id AS patient_id
        ORDER BY patient_id
    """)

    return [
        record["patient_id"]
        for record in result
    ]


def get_patient_data(session, patient_id):

    patient_result = session.run("""
        MATCH (p:Patient {
            patient_id: $patient_id
        })

        RETURN
            p.patient_id AS patient_id,
            p.age AS age,
            p.sex AS sex,
            p.t1d_duration AS t1d_duration
    """, patient_id=patient_id)

    patient = patient_result.single()

    timeline_result = session.run("""
        MATCH (p:Patient {
            patient_id: $patient_id
        })
        -[:HAS_VISIT]->
        (v:Visit)
        -[:HAS_MEASUREMENT]->
        (m:Measurement)
        -[:INSTANCE_OF]->
        (c:Concept)

        RETURN
            v.date AS date,
            c.name AS concept,
            m.value AS value,
            m.unit AS unit

        ORDER BY date
    """, patient_id=patient_id)

    visits = {}

    for record in timeline_result:

        date = str(record["date"])

        if date not in visits:
            visits[date] = {
                "date": date
            }

        visits[date][record["concept"]] = record["value"]

    timeline = list(visits.values())

    kg_result = session.run("""
        MATCH (c1:Concept)
              -[r:CLINICAL_RELATIONSHIP]->
              (c2:Concept)

        RETURN
            c1.name AS source,
            r.relation AS relation,
            c2.name AS target,
            r.evidence_id AS evidence_id,
            r.population AS population,
            r.confidence AS confidence
    """)

    relationships = [
        dict(record)
        for record in kg_result
    ]

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

    evidence = [
        dict(record)
        for record in evidence_result
    ]

    return {
        "patient": dict(patient),
        "timeline": timeline,
        "kg_relationships": relationships,
        "evidence": evidence
    }


def build_reasoning_packet(data):

    temporal = analyze_patient(
        data["timeline"]
    )

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

    prompt = f"""
You are an evidence-grounded clinical reasoning assistant.

You are reviewing a synthetic pediatric Type 1 diabetes
patient for longitudinal kidney-risk assessment.

Use ONLY the structured temporal findings and clinical
knowledge supplied below.

Do not invent medical relationships.
Do not diagnose the patient.
Do not convert risk signals into confirmed disease.
Do not treat a single abnormal value as persistent disease.
Clearly distinguish observed findings from interpretation.

Return the response using exactly these sections:

CLINICAL SUMMARY
TRAJECTORY
KEY FINDINGS
CLINICAL INTERPRETATION
WHAT TO REVIEW
EVIDENCE

Keep the output concise and clinician-facing.

Structured reasoning packet:

{json.dumps(packet, indent=2, default=str)}
"""

    response = azure_client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an evidence-grounded clinical "
                    "reasoning assistant."
                )
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

        with neo4j_driver.session(
            database=os.getenv(
                "KIDNEY_NEO4J_DATABASE"
            )
        ) as session:

            patient_ids = get_patient_ids(
                session
            )

            for patient_id in patient_ids:

                print("\n")
                print("=" * 80)
                print(f"CLINICIAN VIEW — {patient_id}")
                print("=" * 80)

                data = get_patient_data(
                    session,
                    patient_id
                )

                packet = build_reasoning_packet(
                    data
                )

                print(
                    generate_clinical_output(
                        packet
                    )
                )

    finally:

        neo4j_driver.close()


if __name__ == "__main__":
    main()