
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Industrial AI Agent is running!"


def test_successful_investigation_response():
    mock_result = {
        "status": "success",
        "machine_name": "Motor-01",
        "fault_description": "Motor temperature is increasing.",
        "report_source": "qwen3",
        "log_analysis": {"max_temperature": 91},
        "retrieved_sections": [],
        "safety_instructions_included": True,
        "report": "Example investigation report.",
        "evidence_check_passed": True,
        "evidence_issues": [],
        "message": None,
        "error": None,
    }

    with patch(
        "backend.main.investigate_machine_fault",
        return_value=mock_result,
    ) as mock_investigate:
        response = client.post(
            "/investigate",
            json={
                "machine_name": "Motor-01",
                "fault_description": "Motor temperature is increasing.",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["report_source"] == "qwen3"
    assert response.json()["evidence_check_passed"] is True

    mock_investigate.assert_called_once_with(
        machine_name="Motor-01",
        fault_description="Motor temperature is increasing.",
    )


def test_missing_machine_name():
    response = client.post(
        "/investigate",
        json={
            "fault_description": "Motor is overheating.",
        },
    )

    assert response.status_code == 422


def test_empty_machine_name():
    response = client.post(
        "/investigate",
        json={
            "machine_name": "",
            "fault_description": "Motor is overheating.",
        },
    )

    assert response.status_code == 422


def test_empty_fault_description():
    response = client.post(
        "/investigate",
        json={
            "machine_name": "Motor-01",
            "fault_description": "",
        },
    )

    assert response.status_code == 422


def test_missing_fault_description():
    response = client.post(
        "/investigate",
        json={
            "machine_name": "Motor-01",
        },
    )

    assert response.status_code == 422


def test_validation_failed_response():
    mock_result = {
        "status": "validation_failed",
        "machine_name": "Motor-02",
        "fault_description": "Motor vibration is increasing.",
        "report_source": "qwen3",
        "log_analysis": {},
        "retrieved_sections": [],
        "safety_instructions_included": True,
        "report": "Example report requiring evidence corrections.",
        "evidence_check_passed": False,
        "evidence_issues": ["A cause lacks supporting evidence."],
        "message": "Evidence validation failed.",
        "error": None,
    }

    with patch(
        "backend.main.investigate_machine_fault",
        return_value=mock_result,
    ):
        response = client.post(
            "/investigate",
            json={
                "machine_name": "Motor-02",
                "fault_description": "Motor vibration is increasing.",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "validation_failed"
    assert response.json()["evidence_check_passed"] is False
    assert len(response.json()["evidence_issues"]) == 1


def test_error_response():
    mock_result = {
        "status": "error",
        "machine_name": "Motor-03",
        "fault_description": "Motor is making unusual noise.",
        "report_source": None,
        "log_analysis": None,
        "retrieved_sections": None,
        "safety_instructions_included": None,
        "report": None,
        "evidence_check_passed": None,
        "evidence_issues": [],
        "message": "Investigation could not be completed.",
        "error": "Manual data unavailable.",
    }

    with patch(
        "backend.main.investigate_machine_fault",
        return_value=mock_result,
    ):
        response = client.post(
            "/investigate",
            json={
                "machine_name": "Motor-03",
                "fault_description": "Motor is making unusual noise.",
            },
        )

    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert response.json()["error"] == "Manual data unavailable."


if __name__ == "__main__":
    tests = [
        test_health_endpoint,
        test_successful_investigation_response,
        test_missing_machine_name,
        test_empty_machine_name,
        test_empty_fault_description,
        test_missing_fault_description,
        test_validation_failed_response,
        test_error_response,
    ]

    passed = 0
    failed = 0

    print("=" * 60)
    print("API VALIDATION AND ERROR-HANDLING TESTS")
    print("=" * 60)

    for test in tests:
        try:
            test()
            passed += 1
            print(f"PASS: {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL: {test.__name__}: {exc}")

    print("=" * 60)
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print("Overall:", "PASS" if failed == 0 else "FAIL")
