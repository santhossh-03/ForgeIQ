
from rag.report_formatting import clean_report_formatting


def test_temperature_encoding():
    assert clean_report_formatting(
        "Temperature: 91Ã‚Â°C"
    ) == "Temperature: 91Â°C"


def test_time_separator():
    assert clean_report_formatting(
        "Time: 09:00Ã¢09:05"
    ) == "Time: 09:00â€“09:05"


def test_joined_technical_phrases():
    report = (
        "bearingfailure; Excessivemechanical load; "
        "mechanicalload; alignmentbetween shafts; "
        "vibrationduring operation; Root causenot confirmed."
    )

    cleaned = clean_report_formatting(report)

    assert "bearing failure" in cleaned
    assert "Excessive mechanical" in cleaned
    assert "mechanical load" in cleaned
    assert "alignment between" in cleaned
    assert "vibration during" in cleaned
    assert "Root cause not" in cleaned


def test_punctuation_and_numbered_list():
    report = "vibration,and noise\n1.Check the mounting bolts."

    cleaned = clean_report_formatting(report)

    assert "vibration, and noise" in cleaned
    assert "1. Check the mounting bolts." in cleaned


def test_bold_markdown_headings_are_preserved():
    report = (
        "**OBSERVED FACTS**\n"
        "**POSSIBLE CAUSES**\n"
        "**RECOMMENDED INSPECTIONS**\n"
        "**SAFETY**"
    )

    assert clean_report_formatting(report) == report


def test_bold_text_in_list_is_preserved():
    report = (
        "- **Damaged bearings**\n"
        "- **Motor misalignment**"
    )

    assert clean_report_formatting(report) == report


def test_missing_bullet_space_is_fixed():
    report = (
        "-Vibration increased\n"
        "*Check the bearings\n"
        "+Inspect alignment"
    )

    expected = (
        "- Vibration increased\n"
        "* Check the bearings\n"
        "+ Inspect alignment"
    )

    assert clean_report_formatting(report) == expected


def test_valid_technical_text_is_preserved():
    report = "Motor temperature is 91Â°C. Inspect the bearings."

    assert clean_report_formatting(report) == report


def test_wrong_input_type():
    try:
        clean_report_formatting(None)
    except TypeError:
        pass
    else:
        raise AssertionError(
            "Expected TypeError for non-string input"
        )


def test_cleanup_is_repeatable():
    report = (
        "**OBSERVED FACTS**\n"
        "-bearingfailure at 09:00Ã¢09:05; "
        "temperature 91Ã‚Â°C"
    )

    once = clean_report_formatting(report)
    twice = clean_report_formatting(once)

    assert once == twice
    assert "**OBSERVED FACTS**" in once


def test_joined_sensor_trend_word_is_fixed():
    report = (
        "Temperature, vibration, and current allincreased together."
    )

    cleaned = clean_report_formatting(report)

    assert "all increased together" in cleaned


def test_note_is_not_converted_to_bullet():
    report = "*Note: Root cause not confirmed."

    cleaned = clean_report_formatting(report)

    assert cleaned == "Note: Root cause not confirmed."


if __name__ == "__main__":
    tests = [
        test_temperature_encoding,
        test_time_separator,
        test_joined_technical_phrases,
        test_punctuation_and_numbered_list,
        test_bold_markdown_headings_are_preserved,
        test_bold_text_in_list_is_preserved,
        test_missing_bullet_space_is_fixed,
        test_valid_technical_text_is_preserved,
        test_wrong_input_type,
        test_cleanup_is_repeatable,
        test_joined_sensor_trend_word_is_fixed,
        test_note_is_not_converted_to_bullet,
    ]

    passed = 0
    failed = 0

    print("=" * 55)
    print("REPORT FORMATTING TESTS")
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
