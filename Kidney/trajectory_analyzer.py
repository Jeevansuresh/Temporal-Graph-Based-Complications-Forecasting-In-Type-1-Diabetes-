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


def get_patient_timeline(session, patient_id):

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


def generate_clinical_flags(trends):

    flags = []

    if "UACR" in trends:

        uacr = trends["UACR"]

        if uacr["latest"] > 30:

            flags.append(
                "Latest UACR is above 30 mg/g"
            )

        if uacr["direction"] == "INCREASING":

            flags.append(
                "UACR is consistently increasing"
            )

    if "HbA1c" in trends:

        if trends["HbA1c"]["direction"] == "INCREASING":

            flags.append(
                "HbA1c is consistently increasing"
            )

    if "CGM_Time_in_Range" in trends:

        if trends["CGM_Time_in_Range"]["direction"] == "DECREASING":

            flags.append(
                "CGM time-in-range is consistently decreasing"
            )

    if "Systolic_BP" in trends:

        if trends["Systolic_BP"]["direction"] == "INCREASING":

            flags.append(
                "Systolic BP is consistently increasing"
            )

    if "Diastolic_BP" in trends:

        if trends["Diastolic_BP"]["direction"] == "INCREASING":

            flags.append(
                "Diastolic BP is consistently increasing"
            )

    if "Serum_Creatinine" in trends:

        if trends["Serum_Creatinine"]["direction"] == "INCREASING":

            flags.append(
                "Serum creatinine is consistently increasing"
            )

    if "eGFR" in trends:

        if trends["eGFR"]["direction"] == "DECREASING":

            flags.append(
                "eGFR is consistently decreasing"
            )

    return flags


def evaluate_latest_uacr(timeline):

    dates = sorted(timeline.keys())

    records = [
        (
            date,
            timeline[date]["UACR"]
        )
        for date in dates
        if "UACR" in timeline[date]
    ]

    if not records:

        return {
            "rule": "R001",
            "satisfied": False,
            "value": None,
            "date": None
        }

    date, value = records[-1]

    return {
        "rule": "R001",
        "satisfied": value > 30,
        "value": value,
        "date": date
    }


def evaluate_uacr_persistence(timeline):

    dates = sorted(timeline.keys())

    records = [
        (
            date,
            timeline[date]["UACR"]
        )
        for date in dates
        if "UACR" in timeline[date]
    ]

    if len(records) < 3:

        return {
            "rule": "R002",
            "satisfied": False,
            "elevated_count": 0,
            "measurements": records,
            "reason": "Fewer than 3 UACR measurements"
        }

    last_three = records[-3:]

    elevated_count = sum(
        value > 30
        for _, value in last_three
    )

    satisfied = elevated_count >= 2

    if satisfied:

        reason = (
            "At least 2 of the last 3 UACR "
            "values exceed 30 mg/g"
        )

    else:

        reason = (
            "Fewer than 2 of the last 3 UACR "
            "values exceed 30 mg/g"
        )

    return {
        "rule": "R002",
        "satisfied": satisfied,
        "elevated_count": elevated_count,
        "measurements": last_three,
        "reason": reason
    }


def evaluate_screening_eligibility(
    session,
    patient_id
):

    result = session.run("""
        MATCH (p:Patient {patient_id: $patient_id})

        RETURN
            p.age AS age,
            p.t1d_duration AS t1d_duration
    """, patient_id=patient_id)

    record = result.single()

    if record is None:

        return {
            "rule": "R004",
            "satisfied": False,
            "age": None,
            "t1d_duration": None
        }

    age = record["age"]
    duration = record["t1d_duration"]

    return {
        "rule": "R004",
        "satisfied": (
            age >= 11
            and duration >= 5
        ),
        "age": age,
        "t1d_duration": duration
    }


def calculate_trajectory_signal(trends):

    score = 0

    if "UACR" in trends:

        if trends["UACR"]["direction"] in [
            "INCREASING",
            "MOSTLY_INCREASING"
        ]:

            score += 2

        if trends["UACR"]["latest"] > 30:

            score += 2

    if "HbA1c" in trends:

        if trends["HbA1c"]["direction"] in [
            "INCREASING",
            "MOSTLY_INCREASING"
        ]:

            score += 1

    if "CGM_Time_in_Range" in trends:

        if trends["CGM_Time_in_Range"]["direction"] in [
            "DECREASING",
            "MOSTLY_DECREASING"
        ]:

            score += 1

    if "Systolic_BP" in trends:

        if trends["Systolic_BP"]["direction"] in [
            "INCREASING",
            "MOSTLY_INCREASING"
        ]:

            score += 1

    if "eGFR" in trends:

        if trends["eGFR"]["direction"] in [
            "DECREASING",
            "MOSTLY_DECREASING"
        ]:

            score += 1

    if score >= 6:

        level = "HIGH"

    elif score >= 3:

        level = "MODERATE"

    elif score >= 1:

        level = "LOW"

    else:

        level = "NO_SIGNAL"

    return score, level


def print_trends(trends):

    print(
        "\n" + "=" * 70
    )

    print(
        "TEMPORAL TRAJECTORY ANALYSIS"
    )

    print(
        "=" * 70
    )

    for variable, data in trends.items():

        print(
            f"\n{variable}"
        )

        print(
            "-" * 40
        )

        print(
            "Values:",
            " -> ".join(
                str(value)
                for value in data["values"]
            )
        )

        print(
            "Direction:",
            data["direction"]
        )

        print(
            "Directionality:",
            data["directionality"]
        )

        print(
            "First:",
            data["first"]
        )

        print(
            "Latest:",
            data["latest"]
        )

        print(
            "Absolute change:",
            round(
                data["absolute_change"],
                2
            )
        )

        if data["percentage_change"] is not None:

            print(
                "Percentage change:",
                round(
                    data["percentage_change"],
                    2
                ),
                "%"
            )


def print_rule_results(
    latest_uacr,
    persistence,
    screening
):

    print(
        "\n" + "=" * 70
    )

    print(
        "CLINICAL RULE EVALUATION"
    )

    print(
        "=" * 70
    )

    print(
        "\nR001 — Elevated UACR"
    )

    print(
        "Satisfied:",
        latest_uacr["satisfied"]
    )

    print(
        "Latest UACR:",
        latest_uacr["value"],
        "mg/g"
    )

    print(
        "Date:",
        latest_uacr["date"]
    )

    print(
        "\nR002 — Persistent Albuminuria"
    )

    print(
        "Satisfied:",
        persistence["satisfied"]
    )

    print(
        "Elevated count:",
        persistence["elevated_count"]
    )

    print(
        "Measurements:",
        persistence["measurements"]
    )

    print(
        "Reason:",
        persistence["reason"]
    )

    print(
        "\nR004 — Kidney Screening Eligibility"
    )

    print(
        "Satisfied:",
        screening["satisfied"]
    )

    print(
        "Age:",
        screening["age"]
    )

    print(
        "T1D Duration:",
        screening["t1d_duration"],
        "years"
    )


def main():

    patient_id = "P001"

    try:

        driver.verify_connectivity()

        print("CONNECTED")

        with driver.session(
            database=os.getenv(
                "KIDNEY_NEO4J_DATABASE"
            )
        ) as session:

            timeline = get_patient_timeline(
                session,
                patient_id
            )

            if not timeline:

                print(
                    "NO PATIENT DATA FOUND"
                )

                return

            print(
                f"\nPATIENT: {patient_id}"
            )

            print(
                f"VISITS: {len(timeline)}"
            )

            trends = calculate_trends(
                timeline
            )

            print_trends(
                trends
            )

            worsening_variables = (
                determine_worsening_variables(
                    trends
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

            for variable in worsening_variables:

                print(
                    "-",
                    variable
                )

            flags = generate_clinical_flags(
                trends
            )

            print(
                "\n" + "=" * 70
            )

            print(
                "CLINICAL FLAGS"
            )

            print(
                "=" * 70
            )

            for flag in flags:

                print(
                    "-",
                    flag
                )

            latest_uacr = (
                evaluate_latest_uacr(
                    timeline
                )
            )

            persistence = (
                evaluate_uacr_persistence(
                    timeline
                )
            )

            screening = (
                evaluate_screening_eligibility(
                    session,
                    patient_id
                )
            )

            print_rule_results(
                latest_uacr,
                persistence,
                screening
            )

            score, level = (
                calculate_trajectory_signal(
                    trends
                )
            )

            print(
                "\n" + "=" * 70
            )

            print(
                "TEMPORAL RENAL-RISK SIGNAL"
            )

            print(
                "=" * 70
            )

            print(
                "Score:",
                score
            )

            print(
                "Level:",
                level
            )

    finally:

        driver.close()


if __name__ == "__main__":
    main()