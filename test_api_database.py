
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from database.connection import initialize_database
from database.models import get_investigation


def test_api_saves_investigation_and_returns_history():
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "api_test.db"

        # Redirect database operations to an isolated test database.
        with (
            patch("backend.main.initialize_database") as mock_initialize,
            patch("backend.main.save_investigation") as mock_save,
            patch("backend.main.list_investigations") as mock_list,
            patch("backend.main.get_investigation") as mock_get,
        ):
            mock_initialize.side_effect = lambda: initialize_database(db_path)
            mock_save.side_effect = lambda result: save_to_test_database(
                result, db_path
            )
            mock_list.side_effect = lambda limit=50: list_from_test_database(
                limit, db_path
            )
            mock_get.side_effect = lambda investigation_id: get_investigation(
                investigation_id, db_path
            )

            with TestClient(app) as client:
                result = {
                    "status": "success",
                    "machine_name": "Motor-01",
                    "fault_description": "Temperature is increasing.",
                    "report_source": "qwen3",
                    "log_analysis": {"max_temperature": 91},
                    "retrieved_sections": [],
                    "safety_instructions_included": True,
                    "report": "Example report.",
                    "evidence_check_passed": True,
                    "evidence_issues": [],
                    "message": None,
                    "error": None,
                }

                with patch(
                    "backend.main.investigate_machine_fault",
                    return_value=result,
                ):
                    response = client.post(
                        "/investigate",
                        json={
                            "machine_name": "Motor-01",
                            "fault_description": "Temperature is increasing.",
                        },
                    )

                assert response.status_code == 200
                investigation_id = response.json()["investigation_id"]
                assert investigation_id > 0

                history_response = client.get("/investigations")

                assert history_response.status_code == 200
                assert len(history_response.json()) == 1
                assert history_response.json()[0]["id"] == investigation_id

                detail_response = client.get(
                    f"/investigations/{investigation_id}"
                )

                assert detail_response.status_code == 200
                detail = detail_response.json()
                assert detail["machine_name"] == "Motor-01"
                assert detail["log_analysis"]["max_temperature"] == 91
                assert detail["evidence_issues"] == []

                missing_response = client.get("/investigations/9999")
                assert missing_response.status_code == 404


def save_to_test_database(result, db_path):
    from database.models import save_investigation

    return save_investigation(result, db_path)


def list_from_test_database(limit, db_path):
    from database.models import list_investigations

    return list_investigations(limit, db_path)


if __name__ == "__main__":
    try:
        test_api_saves_investigation_and_returns_history()
        print("PASS: API database persistence and history")
        print("Tests passed: 1/1")
        print("Tests failed: 0/1")
        print("Overall: PASS")
    except Exception as exc:
        print("FAIL: API database persistence and history")
        print(f"Reason: {exc}")
        print("Tests passed: 0/1")
        print("Tests failed: 1/1")
        print("Overall: FAIL")
        raise
