
import re


# ============================================================
# SHARED HELPERS
# ============================================================

REPORT_SECTIONS = [
    "OBSERVED FACTS",
    "POSSIBLE CAUSES",
    "CONFIRMATION EVIDENCE",
    "RECOMMENDED INSPECTIONS",
    "SAFETY",
    "NOTE",
]


def build_heading_pattern(heading):
    """Match plain, bold Markdown, or ATX Markdown headings."""

    return re.compile(
        rf"(?im)^\s*(?:#{{1,6}}\s*)?"
        rf"(?:\*\*|__)?{re.escape(heading)}(?:\*\*|__)?"
        rf"\s*:?\s*$"
    )


def extract_section(report, heading):
    """Return a section's content up to the next known heading."""

    if not isinstance(report, str):
        return None

    heading_pattern = build_heading_pattern(heading)
    match = heading_pattern.search(report)

    if not match:
        return None

    next_heading_pattern = re.compile(
        r"(?im)^\s*(?:#{1,6}\s*)?(?:\*\*|__)?(?:"
        + "|".join(re.escape(section) for section in REPORT_SECTIONS)
        + r")(?:\*\*|__)?\s*:?\s*$"
    )

    next_match = next_heading_pattern.search(report, match.end())
    end = next_match.start() if next_match else len(report)

    return report[match.end():end].strip()


def get_manual_text(retrieved_sections):
    """Combine retrieved manual sections into searchable text."""

    return " ".join(
        section.get("text", "")
        for section in retrieved_sections
        if isinstance(section, dict)
    ).lower()


def numbered_items(section_text):
    """Extract numbered list items from a report section."""

    return re.findall(
        r"(?m)^\s*\d+[.)]\s*(.+)$",
        section_text or "",
    )


def contains_any(text, keywords):
    """Return True if any keyword occurs in the supplied text."""

    text = text.lower()
    return any(keyword in text for keyword in keywords)


# ============================================================
# 1. REQUIRED SECTIONS AND CONTENT
# ============================================================

def validate_required_sections(report):
    """Require all essential report headings."""

    required_sections = [
        "OBSERVED FACTS",
        "POSSIBLE CAUSES",
        "RECOMMENDED INSPECTIONS",
        "SAFETY",
    ]

    issues = []

    for heading in required_sections:
        if extract_section(report, heading) is None:
            issues.append(
                f"Required report section {heading!r} is missing."
            )

    return issues


# ============================================================
# 2. SENSOR VALUE VALIDATION
# ============================================================

def validate_sensor_values(report, log_analysis):
    """Reject sensor values not found in the log evidence."""

    issues = []
    known_values = set()

    relevant_keys = (
        "temperature",
        "vibration",
        "current",
        "value",
        "change",
        "first_value",
        "latest_value",
    )

    def collect_values(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and any(word in key.lower() for word in relevant_keys)
                ):
                    known_values.add(float(value))

                elif isinstance(value, (dict, list)):
                    collect_values(value)

        elif isinstance(data, list):
            for item in data:
                collect_values(item)

    collect_values(log_analysis)

    pattern = re.compile(
        r"(?<![\w.])"
        r"(-?\d+(?:\.\d+)?)"
        r"\s*(?:°\s*C|mm/s|A|amps?)\b",
        re.IGNORECASE,
    )

    for match in pattern.finditer(report):
        value = float(match.group(1))

        if value not in known_values:
            issues.append(
                f"Sensor value {match.group(0)!r} was not found "
                "among the known log evidence values."
            )

    return issues


# ============================================================
# 3. POSSIBLE CAUSE VALIDATION
# ============================================================

# This is keyword-based evidence validation, not semantic proof
# that a manual establishes the cause for the current machine.

CAUSE_EVIDENCE_TERMS = {
    "bearings": [
        "bearing",
        "bearings",
    ],
    "misalignment": [
        "misalignment",
        "misaligned",
        "alignment",
    ],
    "mounting": [
        "mounting bolts",
        "mounting base",
    ],
    "rotor imbalance": [
        "rotor imbalance",
        "imbalance",
    ],
    "installation": [
        "installation",
        "improper installation",
    ],
    "power supply": [
        "power supply",
        "electrical supply",
    ],
    "ventilation": [
        "ventilation",
    ],
    "mechanical load": [
        "mechanical load",
    ],
}

CAUTIOUS_TERMS = [
    "unsupported",
    "not supported",
    "not confirmed",
    "unconfirmed",
    "unverified",
    "not verified",
    "not established",
    "possible",
    "may be",
    "might be",
    "could be",
    "cannot be confirmed",
    "cannot confirm",
    "insufficient evidence",
    "unknown",
]


def validate_possible_causes(report, retrieved_sections):
    """Check numbered causes against retrieved manual text."""

    issues = []
    manual_text = get_manual_text(retrieved_sections)
    causes_section = extract_section(report, "POSSIBLE CAUSES")

    if causes_section is None:
        return issues

    for cause in numbered_items(causes_section):
        cause_lower = cause.lower()

        is_cautious = contains_any(cause_lower, CAUTIOUS_TERMS)

        # Preserve the safeguard for unsupported gearbox claims.
        if "gearbox" in cause_lower and "gearbox" not in manual_text:
            if not is_cautious:
                issues.append(
                    "A gearbox cause is asserted without supporting "
                    "evidence in the retrieved manual."
                )

            continue

        matched_categories = [
            category
            for category, terms in CAUSE_EVIDENCE_TERMS.items()
            if contains_any(cause_lower, terms)
        ]

        if not matched_categories:
            if not is_cautious:
                issues.append(
                    f"Possible cause {cause!r} does not match "
                    "the configured manual-supported cause keywords."
                )

            continue

        # Cautious hypotheses are not treated as confirmed assertions.
        if is_cautious:
            continue

        supported_categories = [
            category
            for category in matched_categories
            if contains_any(
                manual_text,
                CAUSE_EVIDENCE_TERMS[category],
            )
        ]

        if not supported_categories:
            category_names = ", ".join(matched_categories)

            issues.append(
                f"Possible cause {cause!r} matches {category_names!r}, "
                "but the corresponding supporting terms were not found "
                "in the retrieved manual."
            )

    return issues


# ============================================================
# 4. CAUSE CERTAINTY VALIDATION
# ============================================================

def validate_cause_certainty(report):
    """Check that confirmed-cause claims have separate evidence."""

    issues = []

    causes_section = extract_section(report, "POSSIBLE CAUSES")

    if causes_section is None:
        return issues

    evidence_section = extract_section(
        report,
        "CONFIRMATION EVIDENCE",
    )

    # Only treat explicit, standalone structured fields as claims.
    # Natural-language statements such as
    # "Unconfirmed: No direct evidence..." are not confirmation claims.
    confirmation_claims = [
        r"(?im)^\s*confirmed\s*:\s*yes\s*$",
        r"(?im)^\s*unconfirmed\s*:\s*no\s*$",
        r"\bconfirmed root cause\b",
        r"\broot cause is confirmed\b",
        r"\bconfirmed cause\b",
        r"\bdefinitively caused by\b",
    ]

    has_confirmation_claim = any(
        re.search(pattern, causes_section, re.IGNORECASE)
        for pattern in confirmation_claims
    )

    if not has_confirmation_claim:
        return issues

    evidence_text = (evidence_section or "").strip().lower()

    insufficient_terms = [
        "none",
        "not available",
        "not provided",
        "not confirmed",
        "no confirmation evidence",
        "not independently verified",
        "insufficient evidence",
        "unknown",
    ]

    has_insufficient_evidence = contains_any(
        evidence_text,
        insufficient_terms,
    )

    if not evidence_text or has_insufficient_evidence:
        issues.append(
            "A cause is presented as confirmed without "
            "sufficient separate confirmation evidence."
        )

    return issues


# ============================================================
# 5. INSPECTION VALIDATION
# ============================================================

def validate_inspections(report, retrieved_sections):
    """Require inspection recommendations and check manual support."""

    issues = []
    manual_text = get_manual_text(retrieved_sections)

    inspection_section = extract_section(
        report,
        "RECOMMENDED INSPECTIONS",
    )

    if inspection_section is None:
        return [
            "Could not locate the RECOMMENDED INSPECTIONS section."
        ]

    meaningful_lines = [
        line.strip()
        for line in inspection_section.splitlines()
        if line.strip()
        and not re.fullmatch(r"[-*•\d.)\s]+", line.strip())
    ]

    if not meaningful_lines:
        return [
            "The RECOMMENDED INSPECTIONS section is empty. "
            "At least one inspection recommendation is required."
        ]

    inspection_terms = {
        "alignment": [
            "alignment",
            "shaft",
            "coupling",
        ],
        "mounting": [
            "mounting bolts",
            "mounting base",
        ],
        "vibration limits": [
            "vibration",
            "manufacturer limits",
        ],
        "bearings": [
            "bearing",
            "bearings",
        ],
        "ventilation": [
            "ventilation",
        ],
        "power supply": [
            "power supply",
            "electrical supply",
        ],
        "gearbox": [
            "gearbox",
            "gearbox teeth",
            "gearbox inspection",
        ],
        "rotor imbalance": [
            "rotor imbalance",
            "imbalance",
        ],
    }

    inspection_text = inspection_section.lower()

    for inspection, keywords in inspection_terms.items():
        mentioned = contains_any(inspection_text, keywords)
        supported = contains_any(manual_text, keywords)

        if mentioned and not supported:
            issues.append(
                f"Inspection recommendation for {inspection!r} "
                "is not supported by the retrieved manual."
            )

    return issues


# ============================================================
# 6. SAFETY CONTENT VALIDATION
# ============================================================

def validate_safety_section(report):
    """Require meaningful safety instructions, not just a heading."""

    issues = []
    safety_section = extract_section(report, "SAFETY")

    if safety_section is None:
        return issues

    if not safety_section.strip():
        issues.append(
            "The SAFETY section is empty. Safety instructions are required."
        )
        return issues

    safety_keywords = [
        "isolate electrical power",
        "electrical power",
        "lockout-tagout",
        "lockout tagout",
        "manufacturer procedures",
        "qualified personnel",
        "electrical inspections",
        "site safety procedures",
        "safety procedures",
    ]

    if not contains_any(safety_section, safety_keywords):
        issues.append(
            "The SAFETY section does not contain a recognized "
            "electrical isolation, lockout-tagout, or qualified-personnel "
            "instruction."
        )

    return issues


# ============================================================
# 7. CENTRAL VALIDATOR
# ============================================================

def validate_report_evidence(report, log_analysis, retrieved_sections):
    """Run all report checks and return a unified validation result."""

    issues = []

    validators = [
        lambda: validate_required_sections(report),
        lambda: validate_sensor_values(report, log_analysis),
        lambda: validate_possible_causes(report, retrieved_sections),
        lambda: validate_cause_certainty(report),
        lambda: validate_inspections(report, retrieved_sections),
        lambda: validate_safety_section(report),
    ]

    for validator in validators:
        issues.extend(validator())

    return {
        "evidence_check_passed": len(issues) == 0,
        "evidence_issues": issues,
    }
