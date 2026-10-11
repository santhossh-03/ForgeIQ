from unittest.mock import patch

from rag import investigator


# ============================================================
# TEST DATA
# ============================================================

FAKE_LOG_ANALYSIS = {
    "status": "success",
    "machine_name": "Test Motor",
    "number_of_readings": 3,
    "trends": {
        "temperature_c": {
            "first_value": 70,
            "latest_value": 85,
            "change": 15,
            "direction": "increasing",
        }
    },
}

FAKE_CHUNKS = [
    {
        "heading": "Problem 1: Motor overheating",
        "text": "Check cooling and ventilation according to the manual.",
    },
    {
        "heading": "Safety:",
        "text": "Safety:\nIsolate electrical power before inspection.",
    },
]

FAKE_EMBEDDINGS = [
    [0.1, 0.2],
    [0.3, 0.4],
]

FAKE_RETRIEVED_SECTIONS = [
    {
        "heading": "Problem 1: Motor overheating",
        "text": "Check cooling and ventilation according to the manual.",
        "similarity": 0.85,
    },
    {
        "heading": "Safety:",
        "text": "Safety:\nIsolate electrical power before inspection.",
        "similarity": 0.50,
    },
]

FAKE_REPORT = """
OBSERVED FACTS
The test motor has increasing temperature readings.

SENSOR TRENDS
Temperature increased from 70 to 85 degrees Celsius.

CONSECUTIVE READING PATTERN
The readings indicate a temperature increase.

POSSIBLE CAUSES
The retrieved manual identifies cooling and ventilation as troubleshooting areas.
The specific root cause remains unconfirmed.

RECOMMENDED INSPECTIONS
Review the troubleshooting checks in the retrieved manual.

SAFETY
Isolate electrical power before inspection.
""".strip()

FAKE_VALIDATION = {
    "evidence_check_passed": True,
    "evidence_issues": [],
}


# ============================================================
# TEST 1: SUCCESSFUL PIPELINE INTEGRATION
# ============================================================

def test_successful_pipeline():
    print("\n--- TEST 1: SUCCESSFUL PIPELINE INTEGRATION ---")

    with (
        patch.object(
            investigator,
            "analyze_machine_logs",
            return_value=FAKE_LOG_ANALYSIS,
        ) as mock_logs,
        patch.object(
            investigator,
            "load_manual_chunks",
            return_value=FAKE_CHUNKS,
        ) as mock_chunks,
        patch.object(
            investigator,
            "get_document_embeddings",
            return_value=FAKE_EMBEDDINGS,
        ) as mock_embeddings,
        patch.object(
            investigator,
            "retrieve_manual_sections",
            return_value=FAKE_RETRIEVED_SECTIONS,
        ) as mock_retrieval,
        patch.object(
            investigator,
            "generate_investigation_report",
            return_value=(FAKE_REPORT, "python_fallback"),
        ) as mock_report,
        patch.object(
            investigator,
            "validate_report_evidence",
            return_value=FAKE_VALIDATION,
        ) as mock_validation,
    ):
        result = investigator.investigate_machine_fault(
            "Test Motor",
            "Motor temperature is increasing.",
        )

    # Verify the pipeline completed successfully.
    assert result["status"] == "success"
    assert result["evidence_check_passed"] is True
    assert result["evidence_issues"] == []
    assert result["report_source"] == "python_fallback"
    assert result["report"] == FAKE_REPORT
    assert result["machine_name"] == "Test Motor"
    assert result["safety_instructions_included"] is True

    # Verify every pipeline stage was called exactly once.
    mock_logs.assert_called_once_with()
    mock_chunks.assert_called_once_with()
    mock_embeddings.assert_called_once_with(FAKE_CHUNKS)

    mock_retrieval.assert_called_once_with(
        "Motor temperature is increasing.",
        FAKE_CHUNKS,
        FAKE_EMBEDDINGS,
    )

    mock_report.assert_called_once_with(
        machine_name="Test Motor",
        fault_description="Motor temperature is increasing.",
        log_analysis=FAKE_LOG_ANALYSIS,
        retrieved_sections=FAKE_RETRIEVED_SECTIONS,
    )

    mock_validation.assert_called_once_with(
        report=FAKE_REPORT,
        log_analysis=FAKE_LOG_ANALYSIS,
        retrieved_sections=FAKE_RETRIEVED_SECTIONS,
    )

    print("PASS: All pipeline stages ran in the expected order.")
    print("PASS: The report and evidence result were returned.")
    print("PASS: Safety-section inclusion was recorded.")
    print("Result status:", result["status"])

    return True


# ============================================================
# TEST 2: LOG ANALYSIS FAILURE STOPS THE PIPELINE
# ============================================================

def test_log_analysis_failure_stops_pipeline():
    print("\n--- TEST 2: LOG ANALYSIS FAILURE ---")

    failed_log_analysis = {
        "status": "error",
        "error": "Simulated log-analysis failure",
    }

    with (
        patch.object(
            investigator,
            "analyze_machine_logs",
            return_value=failed_log_analysis,
        ),
        patch.object(
            investigator,
            "load_manual_chunks",
        ) as mock_chunks,
        patch.object(
            investigator,
            "get_document_embeddings",
        ) as mock_embeddings,
        patch.object(
            investigator,
            "retrieve_manual_sections",
        ) as mock_retrieval,
        patch.object(
            investigator,
            "generate_investigation_report",
        ) as mock_report,
        patch.object(
            investigator,
            "validate_report_evidence",
        ) as mock_validation,
    ):
        result = investigator.investigate_machine_fault(
            "Test Motor",
            "Motor temperature is increasing.",
        )

    assert result["status"] == "error"
    assert "Machine-log analysis failed" in result["error"]

    # Downstream stages must not run after log analysis fails.
    mock_chunks.assert_not_called()
    mock_embeddings.assert_not_called()
    mock_retrieval.assert_not_called()
    mock_report.assert_not_called()
    mock_validation.assert_not_called()

    print("PASS: The pipeline returned an error status.")
    print("PASS: No downstream stage ran after the failure.")
    print("Result status:", result["status"])

    return True


# ============================================================
# TEST RUNNER
# ============================================================

def main():
    tests = [
        ("Successful pipeline integration", test_successful_pipeline),
        ("Log-analysis failure handling", test_log_analysis_failure_stops_pipeline),
    ]

    passed = 0
    failed = 0

    for name, test_function in tests:
        try:
            test_function()
            passed += 1
        except Exception as error:
            failed += 1
            print(f"FAIL: {name}")
            print(f"Reason: {type(error).__name__}: {error}")

    print("\n" + "=" * 55)
    print("INVESTIGATION PIPELINE INTEGRATION TEST SUMMARY")
    print("=" * 55)
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print("Overall:", "PASS" if failed == 0 else "FAIL")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()