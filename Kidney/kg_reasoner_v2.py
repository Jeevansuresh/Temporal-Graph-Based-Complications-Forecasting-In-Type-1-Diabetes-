import os
import json

from dotenv import load_dotenv
from neo4j import GraphDatabase
from openai import OpenAI

from temporal_engine import (
    calculate_trends,
    determine_worsening_variables
)

load_dotenv()


neo4j_driver = GraphDatabase.driver(
    os.getenv("KIDNEY_NEO4J_URI"),
    auth=(
        os.getenv("KIDNEY_NEO4J_USERNAME"),
        os.getenv("KIDNEY_NEO4J_PASSWORD")
    )
)


azure_client = OpenAI(
    api_key=os.getenv(
        "AZURE_OPENAI_API_KEY"
    ),
    base_url=os.getenv(
        "AZURE_OPENAI_ENDPOINT"
    )
)


DEPLOYMENT = os.getenv(
    "AZURE_OPENAI_DEPLOYMENT_MAIN"
)


def get_patient_data(
    session,
    patient_id
):

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


def get_kg_relationships(session):

    result = session.run("""
        MATCH
            (source:Concept)
            -[r:CLINICAL_RELATIONSHIP]->
            (target:Concept)

        RETURN
            source.name AS source,
            r.relation AS relationship,
            target.name AS target,
            r.evidence_id AS evidence_id,
            r.confidence AS confidence,
            r.population AS population
    """)

    return [
        dict(record)
        for record in result
    ]


def get_rules(session):

    result = session.run("""
        MATCH
            (input:Concept)
            -[:INPUT_TO]->
            (rule:Rule)
            -[:PRODUCES]->
            (output:Concept)

        OPTIONAL MATCH
            (rule)
            -[:SUPPORTED_BY]->
            (e:Evidence)

        RETURN
            rule.rule_id AS rule_id,
            rule.trigger AS trigger,
            rule.temporal_requirement
                AS temporal_requirement,
            input.name AS input,
            output.name AS output,
            e.evidence_id AS evidence_id,
            e.citation AS evidence,
            e.population AS population
    """)

    return [
        dict(record)
        for record in result
    ]


def get_evidence(session):

    result = session.run("""
        MATCH (e:Evidence)

        RETURN
            e.evidence_id AS evidence_id,
            e.citation AS citation,
            e.summary AS summary,
            e.population AS population,
            e.evidence_strength
                AS evidence_strength
    """)

    return [
        dict(record)
        for record in result
    ]


def get_patient_context(
    session,
    patient_id
):

    result = session.run("""
        MATCH (p:Patient {patient_id: $patient_id})

        RETURN
            p.patient_id AS patient_id,
            p.age AS age,
            p.sex AS sex,
            p.t1d_duration AS t1d_duration
    """, patient_id=patient_id)

    record = result.single()

    if record is None:
        return {}

    return dict(record)


def build_reasoning_packet(
    patient_context,
    timeline,
    trends,
    worsening_variables,
    relationships,
    rules,
    evidence
):

    relevant_relationships = []

    for relationship in relationships:

        if (
            relationship["source"]
            in worsening_variables
        ):

            relevant_relationships.append(
                relationship
            )

    relevant_rules = []

    for rule in rules:

        if (
            rule["input"]
            in worsening_variables
        ):

            relevant_rules.append(
                rule
            )

    evidence_ids = set()

    for relationship in relevant_relationships:

        if relationship["evidence_id"]:

            evidence_ids.add(
                relationship["evidence_id"]
            )

    for rule in relevant_rules:

        if rule["evidence_id"]:

            evidence_ids.add(
                rule["evidence_id"]
            )

    relevant_evidence = [
        item
        for item in evidence
        if item["evidence_id"]
        in evidence_ids
    ]

    return {

        "patient": patient_context,

        "timeline": timeline,

        "trends": trends,

        "worsening_variables":
            worsening_variables,

        "clinical_relationships":
            relevant_relationships,

        "clinical_rules":
            relevant_rules,

        "evidence":
            relevant_evidence
    }


def ask_azure(
    reasoning_packet
):

    prompt = f"""
You are an evidence-grounded
clinical reasoning research assistant.

You are analyzing a SYNTHETIC pediatric
Type 1 diabetes patient.

You are NOT diagnosing the patient.

Use ONLY the information contained
in the reasoning packet.

Do not invent clinical relationships.

Do not invent thresholds.

Do not convert an association
into a diagnosis.

REASONING PACKET:

{json.dumps(
    reasoning_packet,
    indent=2,
    default=str
)}

Analyze the patient's longitudinal pattern.

Separate your response into:

TEMPORAL FINDINGS:
Describe the important changes over time.

KG-GROUNDED FINDINGS:
Describe only relationships explicitly
present in the supplied KG.

RULE FINDINGS:
Describe which supplied rules are relevant.
Do not claim a rule is satisfied unless
the supplied patient data satisfies it.

JOINT TEMPORAL PATTERN:
Describe whether multiple variables
are changing together.

EVIDENCE CONTEXT:
Mention the population and strength of
the relevant evidence.

INTERPRETATION:
Explain what the combined pattern means
as a research signal.

LIMITATIONS:
Clearly explain evidence limitations,
missing data, and why this is not a diagnosis.

Important:

- Distinguish observed trends from
  KG-supported relationships.
- Distinguish rule-triggered states from
  diagnoses.
- Do not diagnose diabetic kidney disease.
- Do not claim persistent albuminuria
  unless the supplied rule is satisfied.
- Do not invent pediatric applicability
  for adult evidence.
"""

    response = (
        azure_client
        .chat.completions.create(
            model=DEPLOYMENT,
            messages=[
                {
                    "role": "system",
                    "content":
                    "You are an evidence-grounded "
                    "clinical reasoning assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )
    )

    return (
        response
        .choices[0]
        .message
        .content
    )


def main():

    patient_id = "P001"

    try:

        neo4j_driver.verify_connectivity()

        print(
            "NEO4J CONNECTED"
        )

        with neo4j_driver.session(
            database=os.getenv(
                "KIDNEY_NEO4J_DATABASE"
            )
        ) as session:

            patient_context = (
                get_patient_context(
                    session,
                    patient_id
                )
            )

            timeline = (
                get_patient_data(
                    session,
                    patient_id
                )
            )

            trends = (
                calculate_trends(
                    timeline
                )
            )

            worsening_variables = (
                determine_worsening_variables(
                    trends
                )
            )

            relationships = (
                get_kg_relationships(
                    session
                )
            )

            rules = (
                get_rules(
                    session
                )
            )

            evidence = (
                get_evidence(
                    session
                )
            )

            reasoning_packet = (
                build_reasoning_packet(
                    patient_context,
                    timeline,
                    trends,
                    worsening_variables,
                    relationships,
                    rules,
                    evidence
                )
            )

            print(
                "\n" + "=" * 70
            )

            print(
                "PATIENT"
            )

            print(
                "=" * 70
            )

            print(
                json.dumps(
                    patient_context,
                    indent=2,
                    default=str
                )
            )

            print(
                "\n" + "=" * 70
            )

            print(
                "WORSENING VARIABLES"
            )

            print(
                "=" * 70
            )

            for variable in (
                worsening_variables
            ):

                print(
                    "-",
                    variable
                )

            print(
                "\n" + "=" * 70
            )

            print(
                "REASONING PACKET"
            )

            print(
                "=" * 70
            )

            print(
                json.dumps(
                    reasoning_packet,
                    indent=2,
                    default=str
                )
            )

            print(
                "\n" + "=" * 70
            )

            print(
                "AZURE OPENAI REASONING"
            )

            print(
                "=" * 70
            )

            answer = ask_azure(
                reasoning_packet
            )

            print(answer)

    finally:

        neo4j_driver.close()


if __name__ == "__main__":

    main()

        