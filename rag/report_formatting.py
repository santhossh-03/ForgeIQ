
import re


KNOWN_WORD_CORRECTIONS = {
    "bearingfailure": "bearing failure",
    "excessivemechanical": "excessive mechanical",
    "mechanicalload": "mechanical load",
    "alignmentbetween": "alignment between",
    "vibrationduring": "vibration during",
    "root causenot": "root cause not",
    "havea": "have a",
    "andisolate": "and isolate",
    "openingsfor": "openings for",
    "electricalpower": "electrical power",
    "manufacturer'sprocedures": "manufacturer's procedures",
    "bearingstress": "bearing stress",
    "excessivevibration": "excessive vibration",
    "allincreased": "all increased",
    "andelevated": "and elevated",
}


def clean_report_formatting(report: str) -> str:
    """
    Repair known encoding, spacing, and list-formatting problems.

    This function changes presentation only. It does not verify
    technical claims or determine whether evidence supports them.
    """
    if not isinstance(report, str):
        raise TypeError("report must be a string")

    cleaned = report

    # 1. Repair known encoding artifacts.
    cleaned = cleaned.replace("Ã‚Â°C", "Â°C")
    cleaned = re.sub(r"(?<=\d)Ã¢(?=\d)", "â€“", cleaned)

    # 2. Repair known joined technical phrases.
    corrections = sorted(
        KNOWN_WORD_CORRECTIONS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )

    for incorrect, correct in corrections:
        pattern = re.compile(re.escape(incorrect), re.IGNORECASE)

        def preserve_initial_capital(match, replacement=correct):
            original = match.group(0)
            if original and original[0].isupper():
                return replacement[0].upper() + replacement[1:]
            return replacement

        cleaned = pattern.sub(preserve_initial_capital, cleaned)

    # 3. Add a missing space after commas.
    cleaned = re.sub(r",(?=\S)", ", ", cleaned)

    # 4. Fix the known alert-label issue.
    cleaned = re.sub(r"\bto(?=[A-Z]{2,}\b)", "to ", cleaned)

    # 5. Fix missing spaces after list markers.
    # Preserve bold Markdown headings and bold text in list items.
    cleaned = re.sub(
        r"(?m)^([ \t]*-(?!-)|[ \t]*\+(?!\+)|[ \t]*\*(?!\*))[ \t]*(?=\S)",
        lambda match: match.group(1) + " ",
        cleaned,
    )

    # 6. Remove an accidental bullet marker from a standalone note.
    cleaned = re.sub(
        r"(?mi)^([ \t]*)\*[ \t]+(?=note\s*:)",
        r"\1",
        cleaned,
    )

    # 7. Fix missing spaces after numbered list markers.
    cleaned = re.sub(
        r"(?m)^([ \t]*\d+\.)[ \t]*(?=\S)",
        r"\1 ",
        cleaned,
    )

    return cleaned
