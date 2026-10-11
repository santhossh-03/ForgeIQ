
from unittest.mock import patch

from rag import investigator


def run_test(name, expected_status, validation_result=None, raise_error=False):
    fake_log_analysis = {
        "status": "success",
        "machine_name": "Test Motor",
    }

    fake_sections = [
        {
            "heading": "Safety:",
            "text": "Isolate power before inspection.",
            "similarity": 0.8,
        }
    ]

    fake_report = (
        "OBSERVED FACTS\n"
        "SENSOR TRENDS\n"
        "CONSECUTIVE READING PATTERN\n"
        "POSSIBLE CAUSES\n"
        "RECOMMENDED INSPECTIONS\n"
        "SAFETY\n"
        "Isolate power before inspection."
    )

    with (
        patch.object(
            investigator,
            "analyze_machine_logs",
            side_effect=RuntimeError("Simulated pipeline error")
            if raise_error
            else None,
            return_value=None if raise_error else fake_log_analysis,
        ),
        patch.object(
            investigator,
            "load_manual_chunks",
            return_value=fake_sections,
        ),
        patch.object(
            investigator,
            "get_document_embeddings",
            return_value=[[0.1, 0.2]],
        ),
        patch.object(
            investigator,
            "retrieve_manual_sections",
            return_value=fake_sections,
        ),
        patch.object(
            investigator,
            "generate_investigation_report",
            return_value=(fake_report, "python_fallback"),
        ),
        patch.object(
            investigator,
            "validate_report_evidence",
            return_value={
                "evidence_check_passed": validation_result,
                "evidence_issues": (
                    [] if validation_result is True
                    else ["Simulated evidence issue"]
                ),
            },
        ),
    ):
        result = investigator.investigate_machine_fault(
            "Test Motor",
            "Motor overheating",
        )

    passed = result.get("status") == expected_status

    print(
        f"{'PASS' if passed else 'FAIL'}: {name} "
        f"(expected={expected_status}, "
        f"actual={result.get('status')})"
    )

    return passed


def main():
    results = [
        run_test(
            "Valid evidence",
            expected_status="success",
            validation_result=True,
        ),
        run_test(
            "Evidence validation failure",
            expected_status="validation_failed",
            validation_result=False,
        ),
        run_test(
            "Pipeline exception",
            expected_status="error",
            raise_error=True,
        ),
    ]

    print()
    print(f"Tests passed: {sum(results)}/{len(results)}")
    print("Overall:", "PASS" if all(results) else "FAIL")


if __name__ == "__main__":
    main()
