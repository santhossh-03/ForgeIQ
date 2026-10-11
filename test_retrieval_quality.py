
from rag.investigator import (
    load_manual_chunks,
    get_document_embeddings,
    retrieve_manual_sections,
)


# ============================================================
# RETRIEVAL QUALITY TEST CASES
# ============================================================

TEST_CASES = [
    {
        "name": "Specific overheating query",
        "query": (
            "The motor temperature is rising and the motor "
            "is overheating."
        ),
        "required": [
            "Problem 1: Motor overheating",
            "Safety:",
        ],
        "forbidden": [
            "Problem 2: Excessive vibration",
            "Problem 3: Motor misalignment",
        ],
    },
    {
        "name": "Specific misalignment query",
        "query": (
            "The motor shaft and coupling may be misaligned."
        ),
        "required": [
            "Problem 3: Motor misalignment",
            "Safety:",
        ],
        "forbidden": [
            "Problem 1: Motor overheating",
        ],
    },
    {
        "name": "Vibration query",
        "query": (
            "The motor has excessive vibration and may have "
            "loose mounting bolts."
        ),
        "required": [
            "Problem 2: Excessive vibration",
            "Safety:",
        ],
        "forbidden": [],
    },
    {
        "name": "Multiple sensor symptoms",
        "query": (
            "Motor temperature, vibration, and current are "
            "increasing together. Investigate possible mechanical "
            "load, bearing, ventilation, and alignment problems."
        ),
        "required": [
            "Problem 1: Motor overheating",
            "Problem 2: Excessive vibration",
            "Problem 3: Motor misalignment",
            "Safety:",
        ],
        "forbidden": [],
    },
]


def normalize_heading(heading):
    """Normalize headings for case-insensitive comparison."""
    return heading.strip().lower()


def main():
    print("=" * 60)
    print("RAG RETRIEVAL QUALITY TESTS")
    print("=" * 60)

    chunks = load_manual_chunks()
    embeddings = get_document_embeddings(chunks)

    print(f"\nManual chunks loaded: {len(chunks)}")
    print("Embeddings are ready.")

    passed = 0
    failed = 0

    for test in TEST_CASES:
        print("\n" + "=" * 60)
        print(f"TEST: {test['name']}")
        print(f"Query: {test['query']}")
        print("-" * 60)

        retrieved = retrieve_manual_sections(
            fault_description=test["query"],
            chunks=chunks,
            document_embeddings=embeddings,
        )

        retrieved_headings = [
            normalize_heading(section["heading"])
            for section in retrieved
        ]

        print("\nRetrieved sections:")

        for rank, section in enumerate(retrieved, start=1):
            print(
                f"{rank}. {section['heading']} "
                f"(similarity: {section['similarity']})"
            )

        issues = []

        # Check that every required section was retrieved.
        for required_heading in test["required"]:
            expected = normalize_heading(required_heading)

            if expected not in retrieved_headings:
                issues.append(
                    f"Missing required section: {required_heading}"
                )

        # Check that clearly irrelevant sections were excluded.
        for forbidden_heading in test["forbidden"]:
            forbidden = normalize_heading(forbidden_heading)

            if forbidden in retrieved_headings:
                issues.append(
                    f"Unexpected section retrieved: {forbidden_heading}"
                )

        if issues:
            print("\nQUALITY CHECK: FAIL")

            for issue in issues:
                print(f"- {issue}")

            failed += 1
        else:
            print("\nQUALITY CHECK: PASS")
            passed += 1

    # Final summary.
    total = len(TEST_CASES)

    print("\n" + "=" * 60)
    print("RETRIEVAL QUALITY SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {passed}/{total}")
    print(f"Tests failed: {failed}/{total}")

    if failed == 0:
        print("OVERALL RESULT: PASS")
    else:
        print("OVERALL RESULT: FAIL")


if __name__ == "__main__":
    main()
