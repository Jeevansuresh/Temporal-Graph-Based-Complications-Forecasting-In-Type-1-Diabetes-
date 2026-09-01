patient = {
    "patient_id": "P001",
    "age": 15,
    "sex": "M",
    "t1d_duration": 7
}

timeline = [
    {
        "date": "2025-01-15",
        "hba1c": 7.2,
        "cgm_time_in_range": 72,
        "systolic_bp": 112,
        "diastolic_bp": 70,
        "uacr": 14,
        "serum_creatinine": 0.72,
        "egfr": 118
    },
    {
        "date": "2025-04-15",
        "hba1c": 7.8,
        "cgm_time_in_range": 67,
        "systolic_bp": 116,
        "diastolic_bp": 72,
        "uacr": 21,
        "serum_creatinine": 0.74,
        "egfr": 115
    },
    {
        "date": "2025-07-15",
        "hba1c": 8.3,
        "cgm_time_in_range": 61,
        "systolic_bp": 121,
        "diastolic_bp": 76,
        "uacr": 29,
        "serum_creatinine": 0.77,
        "egfr": 111
    },
    {
        "date": "2025-10-15",
        "hba1c": 8.8,
        "cgm_time_in_range": 55,
        "systolic_bp": 128,
        "diastolic_bp": 80,
        "uacr": 36,
        "serum_creatinine": 0.81,
        "egfr": 106
    }
]

print("PATIENT")
print("=" * 50)

print(f"Patient ID: {patient['patient_id']}")
print(f"Age: {patient['age']}")
print(f"Sex: {patient['sex']}")
print(f"T1D Duration: {patient['t1d_duration']} years")

print("\nTIMELINE")
print("=" * 50)

for record in timeline:
    print(record)