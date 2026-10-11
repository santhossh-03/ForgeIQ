
from rag.report_validator import validate_report_evidence


# ============================================================
# 1. SHARED TEST DATA
# ============================================================

log_analysis = {
    "highest_temperature": {"value_c": 91},
    "highest_vibration": {"value_mm_s": 7.2},
    "highest_current": {"value_a": 12.8},
    "trends": {
        "temperature": {
            "first_value": 65,
            "latest_value": 91,
            "change": 26,
        },
        "vibration": {
            "first_value": 2.1,
            "latest_value": 7.2,
            "change": 5.1,
        },
        "current": {
            "first_value": 8.2,
            "latest_value": 12.8,
            "change": 4.6,
        },
    },
}

retrieved_sections = [
    {
        "heading": "Problem 2: Excessive vibration",
        "text": """
        Possible causes:
        - Worn or damaged bearings.
        - Misalignment between the motor and connected equipment.
        - Loose mounting bolts.
        - Rotor imbalance.

        Recommended inspection:
        - Check mounting bolts.
        - Inspect shaft and coupling alignment.
        - Compare vibration with manufacturer limits.
        - Inspect bearings if vibration persists.
        """,
    },
    {
        "heading": "Safety",
        "text": """
        Isolate electrical power before inspection.
        Follow manufacturer procedures and site
        lockout-tagout requirements.
        Qualified personnel must perform electrical inspections.
        """,
    },
]


# ============================================================
# 2. REPORT FIXTURES
# ============================================================

valid_report = """
OBSERVED FACTS
- Highest temperature: 91 °C
- Highest vibration: 7.2 mm/s
- Highest current: 12.8 A

POSSIBLE CAUSES
1. Worn bearings may contribute to excessive vibration.
2. Motor misalignment is another possible explanation.
3. Loose mounting bolts may contribute to vibration.
4. Rotor imbalance is also listed in the manual.

RECOMMENDED INSPECTIONS
1. Inspect bearing condition.
2. Check shaft and coupling alignment.
3. Check mounting bolts.
4. Compare vibration with manufacturer limits.

SAFETY
Isolate electrical power before inspection.
Follow site lockout-tagout procedures.
"""

incorrect_sensor_report = valid_report.replace(
    "91 °C", "150 °C", 1
)

unsupported_cause_report = """
OBSERVED FACTS
- Highest temperature: 91 °C

POSSIBLE CAUSES
1. Damaged gearbox.

RECOMMENDED INSPECTIONS
1. Inspect the bearings.

SAFETY
Isolate electrical power before inspection.
"""

cautious_gearbox_report = """
OBSERVED FACTS
- Highest temperature: 91 °C

POSSIBLE CAUSES
1. Worn bearings may contribute to vibration.

NOTE
A damaged gearbox is an unsupported possible cause
because the retrieved manual does not mention it.

RECOMMENDED INSPECTIONS
1. Inspect bearing condition.

SAFETY
Isolate electrical power before inspection.
"""

confirmed_gearbox_report = """
OBSERVED FACTS
- Highest temperature: 91 °C

POSSIBLE CAUSES
1. The damaged gearbox is the confirmed root cause.

RECOMMENDED INSPECTIONS
1. Inspect the bearings.

SAFETY
Isolate electrical power before inspection.
"""

unconfirmed_no_report = """
OBSERVED FACTS
- Highest temperature: 91 °C
- Highest vibration: 7.2 mm/s
- Highest current: 12.8 A

POSSIBLE CAUSES
1. Worn bearings
   Manual-supported: Yes
   Symptom match: Yes
   Unconfirmed: No

RECOMMENDED INSPECTIONS
1. Inspect bearing condition.

SAFETY
Isolate electrical power before inspection.
"""

not_confirmed_report = """
OBSERVED FACTS
- Highest temperature: 91 °C
- Highest vibration: 7.2 mm/s
- Highest current: 12.8 A

POSSIBLE CAUSES
1. Worn bearings
   Manual-supported: Yes
   Symptom match: Yes
   Unconfirmed: Yes

RECOMMENDED INSPECTIONS
1. Inspect bearing condition for unusual noise or vibration.

SAFETY
Isolate electrical power before inspection.
"""

confirmation_report = """
OBSERVED FACTS
- Highest temperature: 91 °C
- Highest vibration: 7.2 mm/s
- Highest current: 12.8 A

POSSIBLE CAUSES
1. Worn bearings
   Manual-supported: Yes
   Symptom match: Yes
   Confirmed: Yes

CONFIRMATION EVIDENCE
A qualified technician inspected the bearings and documented
visible bearing damage in the maintenance inspection record.

RECOMMENDED INSPECTIONS
1. Review the bearing inspection record.

SAFETY
Follow site safety procedures.
"""

unsupported_inspection_report = """
OBSERVED FACTS
- Highest temperature: 91 °C

POSSIBLE CAUSES
1. Worn bearings may contribute to vibration.

RECOMMENDED INSPECTIONS
1. Inspect the gearbox teeth for damage.

SAFETY
Isolate electrical power before inspection.
"""

missing_safety_report = """
OBSERVED FACTS
- Highest temperature: 91 °C
- Highest vibration: 7.2 mm/s

POSSIBLE CAUSES
1. Worn bearings may contribute to vibration.

RECOMMENDED INSPECTIONS
1. Inspect bearing condition.
2. Check shaft and coupling alignment.
"""

empty_inspections_report = """
OBSERVED FACTS
- Highest temperature: 91 °C
- Highest vibration: 7.2 mm/s

POSSIBLE CAUSES
1. Worn bearings may contribute to vibration.

RECOMMENDED INSPECTIONS

SAFETY
Isolate electrical power before inspection.
"""


# ============================================================
# 3. UNIFIED REGRESSION TEST SUITE
# ============================================================

tests = [
    (
        "TEST 1: VALID REPORT",
        valid_report,
        True,
        None,
    ),
    (
        "TEST 2: INCORRECT SENSOR VALUE",
        incorrect_sensor_report,
        False,
        "sensor value",
    ),
    (
        "TEST 3: UNSUPPORTED NUMBERED CAUSE",
        unsupported_cause_report,
        False,
        "gearbox",
    ),
    (
        "TEST 4: CAUTIOUS GEARBOX NOTE",
        cautious_gearbox_report,
        True,
        None,
    ),
    (
        "TEST 5: CONFIRMED GEARBOX CLAIM",
        confirmed_gearbox_report,
        False,
        "gearbox",
    ),
    (
        "TEST 6: UNCONFIRMED LABEL SET TO NO",
        unconfirmed_no_report,
        False,
        "confirmed",
    ),
    (
        "TEST 7: CAUSE MARKED UNCONFIRMED",
        not_confirmed_report,
        True,
        None,
    ),
    (
        "TEST 8: CONFIRMATION EVIDENCE",
        confirmation_report,
        True,
        None,
    ),
    (
        "TEST 9: UNSUPPORTED INSPECTION",
        unsupported_inspection_report,
        False,
        "gearbox",
    ),
    (
        "TEST 10: MISSING SAFETY SECTION",
        missing_safety_report,
        False,
        "safety",
    ),
    (
        "TEST 11: EMPTY INSPECTIONS",
        empty_inspections_report,
        False,
        "inspection",
    ),
]


# ============================================================
# 4. EXECUTE EVERY TEST, EVEN IF ONE FAILS
# ============================================================

failures = []

for test_name, report, expected_pass, expected_issue in tests:
    try:
        result = validate_report_evidence(
            report,
            log_analysis,
            retrieved_sections,
        )

        actual_pass = result["evidence_check_passed"]
        issues = result["evidence_issues"]

        test_passed = actual_pass == expected_pass

        if expected_issue:
            matching_issue = any(
                expected_issue.lower() in issue.lower()
                for issue in issues
            )
            test_passed = test_passed and matching_issue

        print(f"\n--- {test_name} ---")
        print(result)
        print(f"Expected pass: {expected_pass}")
        print(f"Result: {'PASS' if test_passed else 'FAIL'}")

        if not test_passed:
            failures.append({
                "test": test_name,
                "expected_pass": expected_pass,
                "actual_pass": actual_pass,
                "expected_issue": expected_issue,
                "actual_issues": issues,
            })

    except Exception as exc:
        print(f"\n--- {test_name} ---")
        print(f"ERROR: {exc}")

        failures.append({
            "test": test_name,
            "error": repr(exc),
        })


# ============================================================
# 5. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 50)
print(f"Tests passed: {len(tests) - len(failures)}/{len(tests)}")
print(f"Tests failed: {len(failures)}/{len(tests)}")

if failures:
    print("\nFAILURE DETAILS:")

    for failure in failures:
        print(failure)

    raise SystemExit(1)

print("\nAll report-validator regression tests passed.")
