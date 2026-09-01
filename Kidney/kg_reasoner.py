import os
import json
from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI
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

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_MAIN")




def get_patient_data(session, patient_id):

    result = session.run("""
        MATCH (p:Patient {patient_id: $patient_id})
              -[:HAS_VISIT]->
              (v:Visit)
              -[:HAS_MEASUREMENT]->
              (m:Measurement)
              -[:INSTANCE_OF]->
              (c:Concept)

        RETURN
            v.date AS date,
            c.name AS concept,
            m.value AS value

        ORDER BY date
    """, patient_id=patient_id)

    timeline = {}

    for record in result:
        date = str(record["date"])
        concept = record["concept"]
        value = record["value"]

        if date not in timeline:
            timeline[date] = {}

        timeline[date][concept] = value

    return timeline


def get_clinical_knowledge(session):

    result = session.run("""
        MATCH (a:Concept)-[r:CLINICAL_RELATIONSHIP]->(b:Concept)

        RETURN
            a.name AS source,
            r.relation AS relationship,
            b.name AS target,
            r.evidence_id AS evidence_id,
            r.confidence AS confidence,
            r.population AS population
    """)

    knowledge = []

    for record in result:
        knowledge.append({
            "source": record["source"],
            "relationship": record["relationship"],
            "target": record["target"],
            "evidence_id": record["evidence_id"],
            "confidence": record["confidence"],
            "population": record["population"]
        })

    return knowledge


def calculate_trends(timeline):

    dates = sorted(timeline.keys())

    variables = [
        "UACR",
        "HbA1c",
        "CGM_Time_in_Range",
        "Systolic_BP",
        "eGFR"
    ]

    trends = {}

    for variable in variables:

        values = [
            timeline[date][variable]
            for date in dates
            if variable in timeline[date]
        ]

        if len(values) < 2:
            continue

        changes = [
            values[i] - values[i - 1]
            for i in range(1, len(values))
        ]

        if all(change > 0 for change in changes):
            direction = "INCREASING"

        elif all(change < 0 for change in changes):
            direction = "DECREASING"

        elif sum(change > 0 for change in changes) > sum(change < 0 for change in changes):
            direction = "MOSTLY_INCREASING"

        elif sum(change < 0 for change in changes) > sum(change > 0 for change in changes):
            direction = "MOSTLY_DECREASING"

        else:
            direction = "MIXED"

        trends[variable] = {
            "values": values,
            "direction": direction,
            "first": values[0],
            "latest": values[-1],
            "absolute_change": values[-1] - values[0]
        }

    return trends


def find_relevant_knowledge(trends, knowledge):

    worsening_variables = []

    for variable, data in trends.items():

        direction = data["direction"]

        if variable == "CGM_Time_in_Range":
            worsening = direction in [
                "DECREASING",
                "MOSTLY_DECREASING"
            ]
        else:
            worsening = direction in [
                "INCREASING",
                "MOSTLY_INCREASING"
            ]

        if worsening:
            worsening_variables.append(variable)

    relevant = []

    for item in knowledge:

        if item["source"] in worsening_variables:
            relevant.append(item)

    return relevant


def ask_azure(patient_data, trends, relevant_knowledge):

    prompt = f"""
You are a clinical reasoning research assistant.

You are analyzing a synthetic pediatric Type 1 diabetes patient.

Your task is NOT to diagnose the patient.

Your task is to identify longitudinal renal-risk signals using only:
1. The patient's temporal measurements.
2. The clinical relationships retrieved from the knowledge graph.

PATIENT TIMELINE:
{json.dumps(patient_data, indent=2)}

TEMPORAL TRENDS:
{json.dumps(trends, indent=2)}

CLINICAL KNOWLEDGE GRAPH RELATIONSHIPS:
{json.dumps(relevant_knowledge, indent=2)}

Analyze:

1. Which measurements are worsening over time?
2. Which worsening measurements have a KG relationship to renal risk?
3. Are multiple renal-risk-related variables worsening together?
4. What is the strongest temporal pattern?
5. Are there important limitations or reasons not to interpret this as a diagnosis?

Return the answer in this structure:

TEMPORAL FINDINGS:
- ...

KG-GROUNDED FINDINGS:
- ...

JOINT PATTERN:
- ...

CLINICAL INTERPRETATION:
- ...

LIMITATIONS:
- ...

Do not invent medical relationships that are not present in the supplied knowledge graph.
Do not diagnose diabetic kidney disease.
"""

    response = azure_client.chat.completions.create(
        model=DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "You are an evidence-grounded clinical reasoning assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    return response.choices[0].message.content


try:

    neo4j_driver.verify_connectivity()
    print("NEO4J CONNECTED")

    with neo4j_driver.session(
        database=os.getenv("KIDNEY_NEO4J_DATABASE")
    ) as session:

        patient_id = "P001"

        patient_data = get_patient_data(
            session,
            patient_id
        )

        trends = calculate_trends(
            patient_data
        )

        knowledge = get_clinical_knowledge(
            session
        )

        relevant_knowledge = find_relevant_knowledge(
            trends,
            knowledge
        )

        print("\n" + "=" * 70)
        print("PATIENT TEMPORAL DATA")
        print("=" * 70)

        print(json.dumps(
            patient_data,
            indent=2
        ))

        print("\n" + "=" * 70)
        print("TEMPORAL TRENDS")
        print("=" * 70)

        print(json.dumps(
            trends,
            indent=2
        ))

        print("\n" + "=" * 70)
        print("KG RELATIONSHIPS USED")
        print("=" * 70)

        for item in relevant_knowledge:
            print(item)

        print("\n" + "=" * 70)
        print("AZURE OPENAI REASONING")
        print("=" * 70)

        answer = ask_azure(
            patient_data,
            trends,
            relevant_knowledge
        )

        print(answer)

finally:
    neo4j_driver.close()