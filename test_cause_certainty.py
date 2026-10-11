from rag.report_validator import (
    validate_possible_causes,
    validate_cause_certainty,
)


# The retrieved manual discusses vibration and bearings only.
VIBRATION_MANUAL = [
    {
        "heading": "Problem 2: Excessive vibration",
        "text": (
            "Possible causes include worn bearings, motor misalignment, "
            "loose mounting bolts, and rotor imbalance."
        ),
    },
    {
        "heading": "Safety:",
        "text": "Isolate electrical power before inspection.",
    },
]


def run_test(name, report, retrieved_sections, expected_issue):
    """Check cause evidence and confirmation certainty."""

    evidence_issues = validate_possible_causes(
        report,
        retrieved_sections,
    )

    certainty_issues = validate_cause_certainty(report)

    all_issues = evidence_issues + certainty_issues

    if expected_issue is None:
        passed = not all_issues
    else:
        passed = any(
            expected_issue.lower() in issue.lower()
            for issue in all_issues
        )

    print(f"\n--- {name} ---")
    print("Evidence issues:", evidence_issues)
    print("Certainty issues:", certainty_issues)
    print("Result:", "PASS" if passed else "FAIL")

    if not passed:
        raise AssertionError(
            f"{name} failed. Expected issue: {expected_issue!r}; "
            f"actual issues: {all_issues!r}"
        )


def main():
    # Test 1: A manual-supported possible cause.
    run_test(
        "TEST 1: MANUAL-SUPPORTED BEARING HYPOTHESIS",
        """
POSSIBLE CAUSES
1. Worn bearings may contribute to vibration.
""",
        VIBRATION_MANUAL,
        None,
    )

    # Test 2: A gearbox is not mentioned in the retrieved manual.
    # Explicit uncertainty should prevent a confirmed-cause assertion.
    run_test(
        "TEST 2: UNKNOWN GEARBOX CAUSE",
        """
POSSIBLE CAUSES
1. A damaged gearbox is an unsupported possible cause.
""",
        VIBRATION_MANUAL,
        None,
    )

    # Test 3: The report claims confirmation but has no confirmation
    # evidence section.
    run_test(
        "TEST 3: CONFIRMED CAUSE WITHOUT EVIDENCE",
        """
POSSIBLE CAUSES
1. Confirmed root cause: worn bearings.

""",
        VIBRATION_MANUAL,
        "confirmed without",
    )

    # Test 4: Confirmation is claimed despite explicit lack of evidence.
    run_test(
        "TEST 4: CONFIRMATION CONTRADICTS EVIDENCE SECTION",
        """
POSSIBLE CAUSES
1. Confirmed root cause: worn bearings.

CONFIRMATION EVIDENCE
No confirmation evidence is available.
""",
        VIBRATION_MANUAL,
        "confirmed without",
    )

    # Test 5: A cautious hypothesis can be discussed even when the
    # manual does not mention that component.
    run_test(
        "TEST 5: UNKNOWN COMPONENT LABELLED UNCONFIRMED",
        """
POSSIBLE CAUSES
1. A gearbox fault is unconfirmed and requires further investigation.
""",
        VIBRATION_MANUAL,
        None,
    )

    print("\nAll cause-certainty tests passed.")


if __name__ == "__main__":
    main()