DIRECTIONALITY = {
    "UACR": "higher_is_worse",
    "HbA1c": "higher_is_worse",
    "CGM_Time_in_Range": "lower_is_worse",
    "Systolic_BP": "higher_is_worse",
    "Diastolic_BP": "higher_is_worse",
    "Serum_Creatinine": "higher_is_worse",
    "eGFR": "lower_is_worse"
}


def calculate_trend(values):

    if len(values) < 2:
        return "INSUFFICIENT_DATA"

    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    positive = sum(
        change > 0
        for change in changes
    )

    negative = sum(
        change < 0
        for change in changes
    )

    if positive == len(changes):
        return "INCREASING"

    if negative == len(changes):
        return "DECREASING"

    if positive > negative:
        return "MOSTLY_INCREASING"

    if negative > positive:
        return "MOSTLY_DECREASING"

    return "MIXED"


def calculate_trends(timeline):

    dates = sorted(timeline.keys())

    trends = {}

    for variable in DIRECTIONALITY:

        values = [
            timeline[date][variable]
            for date in dates
            if variable in timeline[date]
        ]

        if len(values) < 2:
            continue

        first = values[0]
        latest = values[-1]

        changes = [
            values[i] - values[i - 1]
            for i in range(1, len(values))
        ]

        if first != 0:
            percentage_change = (
                (latest - first) / first
            ) * 100
        else:
            percentage_change = None

        trends[variable] = {
            "values": values,
            "direction": calculate_trend(values),
            "directionality": DIRECTIONALITY[variable],
            "first": first,
            "latest": latest,
            "absolute_change": latest - first,
            "percentage_change": percentage_change,
            "interval_changes": changes
        }

    return trends


def determine_worsening_variables(trends):

    worsening = []

    for variable, data in trends.items():

        direction = data["direction"]
        directionality = data["directionality"]

        if directionality == "higher_is_worse":

            if direction in [
                "INCREASING",
                "MOSTLY_INCREASING"
            ]:
                worsening.append(variable)

        elif directionality == "lower_is_worse":

            if direction in [
                "DECREASING",
                "MOSTLY_DECREASING"
            ]:
                worsening.append(variable)

    return worsening