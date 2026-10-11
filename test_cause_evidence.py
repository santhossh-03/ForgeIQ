
from rag.report_validator import validate_possible_causes


# Manual evidence intentionally does not mention ventilation or gearbox.
retrieved_sections = [
    {
        "heading": "Problem 2: Excessive vibration",
        "text": """
        Possible causes:
        - Worn or damaged bearings.
        - Misalignment between the motor and connected equipment.
        - Loose mounting bolts.
        - Rotor imbalance.
        """,
    }
]


def run_test(name, cause, expected_issue):
    report = f"""
POSSIBLE CAUSES
1. {cause}
"""

    issues = validate_possible_causes(
        report,
        retrieved_sections,
    )

    failed = any(expected_issue.lower() in issue.lower() for issue in issues)

    passed = failed if expected_issue else not issues

    print(f"\n--- {name} ---")
    print("Cause:", cause)
    print("Issues:", issues)
    print("Result:", "PASS" if passed else "FAIL")

    if not passed:
        raise AssertionError(
            f"{name} failed. Expected issue: {expected_issue!r}; "
            f"actual issues: {issues!r}"
        )


def main():
    run_test(
        "TEST 1: MANUAL-SUPPORTED BEARINGS",
        "Worn bearings may contribute to vibration.",
        None,
    )

    run_test(
        "TEST 2: MANUAL-SUPPORTED MISALIGNMENT",
        "Motor misalignment is a possible explanation.",
        None,
    )

    run_test(
        "TEST 3: UNSUPPORTED VENTILATION ASSERTION",
        "Ventilation failure is the cause.",
        "ventilation",
    )

    run_test(
        "TEST 4: CAUTIOUS GEARBOX HYPOTHESIS",
        "A damaged gearbox is an unsupported possible cause.",
        None,
    )

    run_test(
        "TEST 5: UNSUPPORTED GEARBOX ASSERTION",
        "A damaged gearbox is the confirmed cause.",
        "gearbox",
    )

    print("\nAll cause-evidence tests passed.")


if __name__ == "__main__":
    main()
