
from pathlib import Path
import csv


# 1. Locate the machine log file
LOG_PATH = Path("data/machine_logs/motor_log.txt")


def analyze_machine_logs():
    # 2. Check whether the file exists
    if not LOG_PATH.exists():
        return {
            "status": "error",
            "message": "Machine log file not found."
        }

    # 3. Read the file
    with open(LOG_PATH, "r", encoding="utf-8") as file:
        lines = file.readlines()

    # 4. Find the CSV header
    header_index = None

    for index, line in enumerate(lines):
        if line.startswith("Timestamp,"):
            header_index = index
            break

    if header_index is None:
        return {
            "status": "error",
            "message": "CSV header not found in machine log."
        }

    # 5. Parse the readings as CSV data
    csv_text = "".join(lines[header_index:])
    reader = csv.DictReader(csv_text.splitlines())
    readings = list(reader)

    if not readings:
        return {
            "status": "error",
            "message": "No machine readings found."
        }

    # 6. Convert measurement fields to numbers
    for reading in readings:
        reading["Temperature_C"] = float(
            reading["Temperature_C"]
        )
        reading["Vibration_mm_s"] = float(
            reading["Vibration_mm_s"]
        )
        reading["Motor_Current_A"] = float(
            reading["Motor_Current_A"]
        )

    # 7. Find the highest measurements
    highest_temperature = max(
        readings,
        key=lambda item: item["Temperature_C"]
    )
    highest_vibration = max(
        readings,
        key=lambda item: item["Vibration_mm_s"]
    )
    highest_current = max(
        readings,
        key=lambda item: item["Motor_Current_A"]
    )

    # 8. Collect observed statuses
    statuses = list(dict.fromkeys(
        reading["Status"] for reading in readings
    ))

    # 9. Compare the first and latest readings
    first_reading = readings[0]
    latest_reading = readings[-1]

    def calculate_trend(first_value, latest_value):
        change = round(latest_value - first_value, 2)

        if change > 0:
            direction = "increased"
        elif change < 0:
            direction = "decreased"
        else:
            direction = "unchanged"

        return {
            "first_value": first_value,
            "latest_value": latest_value,
            "change": change,
            "direction": direction
        }

    trends = {
        "temperature_c": calculate_trend(
            first_reading["Temperature_C"],
            latest_reading["Temperature_C"]
        ),
        "vibration_mm_s": calculate_trend(
            first_reading["Vibration_mm_s"],
            latest_reading["Vibration_mm_s"]
        ),
        "motor_current_a": calculate_trend(
            first_reading["Motor_Current_A"],
            latest_reading["Motor_Current_A"]
        )
    }

    # 10. Analyze every consecutive pair of readings
    interval_analysis = []

    for index in range(1, len(readings)):
        previous = readings[index - 1]
        current = readings[index]

        temperature_change = round(
            current["Temperature_C"]
            - previous["Temperature_C"],
            2
        )

        vibration_change = round(
            current["Vibration_mm_s"]
            - previous["Vibration_mm_s"],
            2
        )

        current_change = round(
            current["Motor_Current_A"]
            - previous["Motor_Current_A"],
            2
        )

        all_increased = (
            temperature_change > 0
            and vibration_change > 0
            and current_change > 0
        )

        interval_analysis.append({
            "from_timestamp": previous["Timestamp"],
            "to_timestamp": current["Timestamp"],
            "temperature_change_c": temperature_change,
            "vibration_change_mm_s": vibration_change,
            "motor_current_change_a": current_change,
            "all_three_measurements_increased": all_increased
        })

    # 11. Count intervals where all measurements increased
    simultaneous_increase_count = sum(
        interval["all_three_measurements_increased"]
        for interval in interval_analysis
    )

    # 12. Return the complete analysis
    return {
        "status": "success",
        "machine_name": "Industrial Electric Motor",
        "number_of_readings": len(readings),

        "highest_temperature": {
            "value_c": highest_temperature["Temperature_C"],
            "timestamp": highest_temperature["Timestamp"]
        },
        "highest_vibration": {
            "value_mm_s": highest_vibration["Vibration_mm_s"],
            "timestamp": highest_vibration["Timestamp"]
        },
        "highest_current": {
            "value_a": highest_current["Motor_Current_A"],
            "timestamp": highest_current["Timestamp"]
        },

        "trends": trends,
        "interval_analysis": interval_analysis,
        "simultaneous_increase_intervals": simultaneous_increase_count,
        "observed_statuses": statuses,
        "latest_reading": latest_reading
    }


# 13. Run this file directly for testing
if __name__ == "__main__":
    result = analyze_machine_logs()

    for key, value in result.items():
        print(f"{key}: {value}")
