
import json
import tempfile
from pathlib import Path

from database.connection import initialize_database
from database.models import (
    get_investigation,
    list_investigations,
    save_investigation,
)


def sample_result(machine_name="Motor-01"):
    return {
        "machine_name": machine_name,
        "fault_description": "Motor temperature and vibration are increasing.",
        "status": "success",
        "report_source": "qwen3",
        "log_analysis": {"max_temperature": 91},
        "retrieved_sections": [{"heading": "Motor overheating"}],
        "safety_instructions_included": True,
        "report": "Example investigation report.",
        "evidence_check_passed": True,
        "evidence_issues": [],
        "message": None,
        "error": None,
    }


def test_database_initialization():
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "test.db"

        initialize_database(db_path)
        initialize_database(db_path)

        assert db_path.exists()


def test_save_and_retrieve_investigation():
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "test.db"
        initialize_database(db_path)

        investigation_id = save_investigation(
            sample_result(),
            db_path,
        )

        result = get_investigation(investigation_id, db_path)

        assert result is not None
        assert result["machine_name"] == "Motor-01"
        assert result["status"] == "success"
        assert result["evidence_check_passed"] == 1
        assert json.loads(result["log_analysis"])["max_temperature"] == 91
        assert json.loads(result["evidence_issues"]) == []


def test_list_investigations():
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "test.db"
        initialize_database(db_path)

        save_investigation(sample_result("Motor-01"), db_path)
        save_investigation(sample_result("Motor-02"), db_path)

        results = list_investigations(db_path=db_path)

        assert len(results) == 2
        assert results[0]["machine_name"] == "Motor-02"
        assert results[1]["machine_name"] == "Motor-01"


def test_missing_investigation():
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / "test.db"
        initialize_database(db_path)

        assert get_investigation(999, db_path) is None


def test_invalid_history_limit():
    try:
        list_investigations(limit=0, db_path="unused.db")
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for limit=0")


if __name__ == "__main__":
    tests = [
        test_database_initialization,
        test_save_and_retrieve_investigation,
        test_list_investigations,
        test_missing_investigation,
        test_invalid_history_limit,
    ]

    passed = 0
    failed = 0

    print("=" * 55)
    print("DATABASE INTEGRATION TESTS")
    print("=" * 55)

    for test in tests:
        try:
            test()
            passed += 1
            print(f"PASS: {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL: {test.__name__}: {exc}")

    print("=" * 55)
    print(f"Tests passed: {passed}/{len(tests)}")
    print(f"Tests failed: {failed}/{len(tests)}")
    print("Overall:", "PASS" if failed == 0 else "FAIL")
