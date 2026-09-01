import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

from temporal_engine import (
    calculate_trends,
    determine_worsening_variables
)

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("KIDNEY_NEO4J_URI"),
    auth=(
        os.getenv("KIDNEY_NEO4J_USERNAME"),
        os.getenv("KIDNEY_NEO4J_PASSWORD")
    )
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


def get_patient_info(session, patient_id):

    result = session.run("""
        MATCH (p:Patient {
            patient_id: $patient_id
        })

        RETURN
            p.patient_id AS patient_id,
            p.age AS age,
            p.sex AS sex,
            p.t1d_duration AS t1d_duration
    """, patient_id=patient_id)

    record = result.single()

    if record is None:
        return None

    return dict(record)


def get_patient_timeline(session, patient_id):

    result = session.run("""
        MATCH
            (p:Patient {
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

    timeline = {}

    for record in result:

        date = str(record["date"])

        if date not in timeline:
            timeline[date] = {}

        timeline[date][record["concept"]] = {
            "value": record["value"],
            "unit": record["unit"]
        }

    return timeline


def convert_timeline_for_engine(timeline):

    converted = {}

    for date, measurements in timeline.items():

        converted[date] = {}

        for concept, data in measurements.items():

            converted[date][concept] = data["value"]

    return converted


def print_patient(patient, timeline, trends):

    print()
    print("=" * 75)
    print(f"PATIENT {patient['patient_id']}")
    print("=" * 75)

    print(
        f"Age: {patient['age']} | "
        f"Sex: {patient['sex']} | "
        f"T1D duration: {patient['t1d_duration']} years"
    )

    print()

    print("TEMPORAL GRAPH")
    print("-" * 75)

    for date in sorted(timeline.keys()):

        print(f"\n{date}")

        measurements = timeline[date]

        for concept, data in measurements.items():

            print(
                f"  {concept}: "
                f"{data['value']} {data['unit']}"
            )

    print()

    print("TRAJECTORIES")
    print("-" * 75)

    for variable, data in trends.items():

        change = data["absolute_change"]
        percentage = data["percentage_change"]

        print(
            f"{variable:25} "
            f"{data['first']} -> {data['latest']}   "
            f"{data['direction']:20} "
            f"change={change:+.2f} "
            f"({percentage:+.1f}%)"
        )

    worsening = determine_worsening_variables(
        trends
    )

    print()

    print("WORSENING VARIABLES")
    print("-" * 75)

    if worsening:

        for variable in worsening:
            print(f"  - {variable}")

    else:

        print("  None")


def main():

    try:

        driver.verify_connectivity()

        print("NEO4J CONNECTED")

        with driver.session(
            database=os.getenv(
                "KIDNEY_NEO4J_DATABASE"
            )
        ) as session:

            patient_ids = get_patient_ids(
                session
            )

            print(
                f"\nFOUND {len(patient_ids)} PATIENTS"
            )

            for patient_id in patient_ids:

                patient = get_patient_info(
                    session,
                    patient_id
                )

                timeline = get_patient_timeline(
                    session,
                    patient_id
                )

                engine_timeline = (
                    convert_timeline_for_engine(
                        timeline
                    )
                )

                trends = calculate_trends(
                    engine_timeline
                )

                print_patient(
                    patient,
                    timeline,
                    trends
                )

            print()
            print("=" * 75)
            print("TEMPORAL GRAPH DEMO COMPLETE")
            print("=" * 75)

    finally:

        driver.close()


if __name__ == "__main__":
    main()