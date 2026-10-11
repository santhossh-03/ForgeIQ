
from rag.investigator import (
    load_manual_chunks,
    get_document_embeddings,
    retrieve_manual_sections,
)


TEST_CASES = [
    {
        "name": "Motor overheating",
        "query": (
            "The motor temperature is rising "
            "and the motor is overheating."
        ),
        "expected": "Problem 1: Motor overheating",
    },
    {
        "name": "Excessive vibration",
        "query": (
            "The motor has excessive vibration "
            "and may have loose mounting bolts."
        ),
        "expected": "Problem 2: Excessive vibration",
    },
    {
        "name": "Motor misalignment",
        "query": (
            "The motor shaft and coupling may be misaligned."
        ),
        "expected": "Problem 3: Motor misalignment",
    },
    {
        "name": "Multiple increasing sensor readings",
        "query": (
            "Motor temperature, vibration, and current are increasing "
            "together. Investigate possible mechanical load, bearing, "
            "ventilation, and alignment problems."
        ),
        "expected": "Problem 1: Motor overheating",
    },
    {
        "name": "Unsupported gearbox hypothesis",
        "query": (
            "Could a damaged gearbox explain increasing motor "
            "temperature and vibration? Check the manual for "
            "relevant evidence."
        ),
        "expected": "Problem 2: Excessive vibration",
    },
]


def normalize_heading(heading):
    return heading.strip().lower()


def is_safety_section(section):
    return normalize_heading(section["heading"]) == "safety:"


def main():
    print("=" * 60)
    print("INDUSTRIAL RAG RETRIEVAL TEST SUITE")
    print("=" * 60)

    chunks = load_manual_chunks()
    embeddings = get_document_embeddings(chunks)

    print(f"Manual chunks loaded: {len(chunks)}")

    passed = 0
    failed = 0

    for test in TEST_CASES:
        print("\n" + "=" * 60)
        print(f"TEST: {test['name']}")
        print(f"Query: {test['query']}")

        retrieved = retrieve_manual_sections(
            fault_description=test["query"],
            chunks=chunks,
            document_embeddings=embeddings,
        )

        if not retrieved:
            print("RETRIEVAL CHECK: FAIL — no sections returned.")
            print("RESULT: FAIL")
            failed += 1
            continue

        total_chars = sum(
            len(section["text"])
            for section in retrieved
        )

        print(f"Total retrieved text: {total_chars} characters")

        headings = [
            normalize_heading(section["heading"])
            for section in retrieved
        ]

        # Check 1: Safety context must be present.
        if not any(
            is_safety_section(section)
            for section in retrieved
        ):
            print("SAFETY CHECK: FAIL")
            print("RESULT: FAIL")
            failed += 1
            continue

        print("SAFETY CHECK: PASS")

        # Display the retrieved sections in their returned order.
        print("\nRETRIEVAL RANKING")

        for rank, section in enumerate(retrieved, start=1):
            heading = section["heading"].strip()
            similarity = section["similarity"]

            if is_safety_section(section):
                label = "MANDATORY SAFETY CONTEXT"
            elif normalize_heading(heading) == normalize_heading(
                test["expected"]
            ):
                label = "EXPECTED PRIMARY SECTION"
            else:
                label = "ADDITIONAL SECTION"

            print(
                f"Rank {rank}: {heading} | "
                f"Similarity: {similarity} | {label}"
            )

        # Check 2: Multi-sensor case must cover all three problems.
        if test["name"] == "Multiple increasing sensor readings":
            required = [
                "problem 1: motor overheating",
                "problem 2: excessive vibration",
                "problem 3: motor misalignment",
            ]

            missing = [
                heading
                for heading in required
                if not any(
                    heading in retrieved_heading
                    for retrieved_heading in headings
                )
            ]

            if missing:
                print(
                    "COVERAGE CHECK: FAIL — "
                    f"missing sections: {missing}"
                )
                print("RESULT: FAIL")
                failed += 1
                continue

            print(
                "COVERAGE CHECK: PASS — "
                "all three troubleshooting sections retrieved."
            )

        # Check 3: Expected troubleshooting section must rank first.
        troubleshooting = [
            section
            for section in retrieved
            if not is_safety_section(section)
        ]

        if not troubleshooting:
            print("PRIMARY RANK CHECK: FAIL — no problem sections.")
            print("RESULT: FAIL")
            failed += 1
            continue

        expected = normalize_heading(test["expected"])
        actual_top = normalize_heading(
            troubleshooting[0]["heading"]
        )

        if actual_top != expected:
            print("PRIMARY RANK CHECK: FAIL")
            print(f"Expected first: {expected}")
            print(f"Actually first: {actual_top}")
            print("RESULT: FAIL")
            failed += 1
            continue

        print("PRIMARY RANK CHECK: PASS")

        print("RESULT: PASS")
        passed += 1

    print("\n" + "=" * 60)
    print("FINAL RETRIEVAL TEST SUMMARY")
    print("=" * 60)
    print(f"Retrieval tests passed: {passed}/{len(TEST_CASES)}")
    print(f"Retrieval tests failed: {failed}/{len(TEST_CASES)}")

    if failed == 0:
        print("OVERALL RESULT: PASS")
    else:
        print("OVERALL RESULT: FAIL")


if __name__ == "__main__":
    main()
