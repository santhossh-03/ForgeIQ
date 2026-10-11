
import json
import math
import re
from pathlib import Path

import ollama

from agents.analyze_machine_logs import analyze_machine_logs
from rag.report_validator import validate_report_evidence
from rag.report_formatting import clean_report_formatting


# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

MANUAL_PATH = Path("data/manuals/motor_troubleshooting.txt")
CACHE_PATH = Path("data/cache/manual_embeddings.json")

EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen3:4b-instruct"

TOP_K = 3
NUM_PREDICT = 1600


# ============================================================
# 2. COSINE SIMILARITY
# ============================================================

def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two embedding vectors."""

    if not vector_a or not vector_b:
        return 0.0

    if len(vector_a) != len(vector_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


# ============================================================
# 3. LOAD AND SPLIT THE TROUBLESHOOTING MANUAL
# ============================================================

def load_manual_chunks():
    """Split the manual into problem and safety sections."""

    if not MANUAL_PATH.exists():
        raise FileNotFoundError(
            f"Troubleshooting manual not found: {MANUAL_PATH}"
        )

    manual_text = MANUAL_PATH.read_text(encoding="utf-8").strip()

    if not manual_text:
        raise ValueError("The troubleshooting manual is empty.")

    parts = re.split(
        r"(?=^Problem\s+\d+\s*:|^Safety\s*:)",
        manual_text,
        flags=re.MULTILINE | re.IGNORECASE,
    )

    chunks = []

    for part in parts:
        text = part.strip()

        if not text:
            continue

        first_line = text.splitlines()[0].strip()

        chunks.append({
            "heading": first_line,
            "text": text,
        })

    chunks = [
        chunk
        for chunk in chunks
        if chunk["heading"].strip().lower()
        != "industrial motor troubleshooting manual"
    ]

    if not chunks:
        raise ValueError("No manual sections could be extracted.")

    print(f"Manual chunks created: {len(chunks)}")

    return chunks


# ============================================================
# 4. CREATE OR LOAD CACHED DOCUMENT EMBEDDINGS
# ============================================================

def get_document_embeddings(chunks):
    """Load matching cached embeddings or create new embeddings."""

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)

    signature = json.dumps(
        [chunk["text"] for chunk in chunks],
        ensure_ascii=False,
    )

    if CACHE_PATH.exists():
        try:
            with CACHE_PATH.open("r", encoding="utf-8") as file:
                cached_data = json.load(file)

            cached_embeddings = cached_data.get("embeddings", [])

            if (
                cached_data.get("signature") == signature
                and len(cached_embeddings) == len(chunks)
                and all(
                    isinstance(embedding, list) and embedding
                    for embedding in cached_embeddings
                )
            ):
                print("Loaded document embeddings from cache.")
                return cached_embeddings

        except (json.JSONDecodeError, OSError, AttributeError):
            print("Cache could not be read. Rebuilding embeddings.")

    print("Creating document embeddings...")

    embeddings = []

    for chunk in chunks:
        response = ollama.embed(
            model=EMBEDDING_MODEL,
            input=chunk["text"],
        )

        embedding_list = response.get("embeddings", [])

        if not embedding_list:
            raise RuntimeError(
                f"No embedding returned for: {chunk['heading']}"
            )

        embeddings.append(embedding_list[0])

    cache_data = {
        "signature": signature,
        "embeddings": embeddings,
    }

    with CACHE_PATH.open("w", encoding="utf-8") as file:
        json.dump(cache_data, file)

    print("Document embeddings saved to cache.")

    return embeddings


# ============================================================
# 5. RETRIEVE RELEVANT MANUAL SECTIONS
# ============================================================

def retrieve_manual_sections(
    fault_description,
    chunks,
    document_embeddings,
):
    """Retrieve relevant manual sections and include safety guidance."""

    query_response = ollama.embed(
        model=EMBEDDING_MODEL,
        input=fault_description,
    )

    query_embeddings = query_response.get("embeddings", [])

    if not query_embeddings:
        raise RuntimeError(
            "The embedding model returned no query embedding."
        )

    if len(document_embeddings) != len(chunks):
        raise ValueError(
            "The number of document embeddings does not match "
            "the number of manual chunks."
        )

    query_embedding = query_embeddings[0]
    ranked_sections = []

    for index, chunk in enumerate(chunks):
        similarity = cosine_similarity(
            query_embedding,
            document_embeddings[index],
        )

        ranked_sections.append({
            "heading": chunk["heading"],
            "similarity": round(similarity, 4),
            "text": chunk["text"],
        })

    ranked_sections.sort(
        key=lambda section: section["similarity"],
        reverse=True,
    )

    if not ranked_sections:
        raise ValueError("No manual sections are available for retrieval.")

    print("\n--- RAG RETRIEVAL RANKING ---")

    for rank, section in enumerate(ranked_sections, start=1):
        print(
            f"Rank {rank}: {section['heading']} "
            f"| Similarity: {section['similarity']}"
        )

    relevant_sections = [ranked_sections[0]]
    best_similarity = ranked_sections[0]["similarity"]
    similarity_gap_limit = 0.08

    for section in ranked_sections[1:]:
        heading = section["heading"].strip().lower().rstrip(":")

        if heading == "safety":
            continue

        similarity_gap = best_similarity - section["similarity"]

        if similarity_gap <= similarity_gap_limit:
            relevant_sections.append(section)

    safety_section = next(
        (
            section
            for section in ranked_sections
            if section["heading"].strip().lower().rstrip(":") == "safety"
        ),
        None,
    )

    if safety_section:
        safety_already_included = any(
            section["heading"].strip().lower().rstrip(":") == "safety"
            for section in relevant_sections
        )

        if not safety_already_included:
            relevant_sections.append(safety_section)

    print("\n--- SELECTED MANUAL SECTIONS ---")

    for section in relevant_sections:
        print(
            f"{section['heading']} "
            f"| Similarity: {section['similarity']}"
        )

    return relevant_sections


# ============================================================
# 6. FORMAT VALUES FROM MACHINE LOG ANALYSIS
# ============================================================

def format_sensor_value(data, key, value_key, unit):
    """Format a sensor summary without assuming a value exists."""

    item = data.get(key)

    if not isinstance(item, dict):
        return f"{key}: unavailable"

    value = item.get(value_key, "unavailable")
    timestamp = item.get("timestamp", "unknown time")

    return f"{key}: {value} {unit} at {timestamp}"


def format_log_analysis(log_analysis):
    """Format machine-log results as readable evidence for the LLM."""

    if not isinstance(log_analysis, dict):
        return str(log_analysis)

    lines = [
        f"Machine: {log_analysis.get('machine_name', 'Unknown')}",
        (
            "Number of readings: "
            f"{log_analysis.get('number_of_readings', 'Unknown')}"
        ),
    ]

    sensor_definitions = [
        ("highest_temperature", "value_c", "°C", "Highest temperature"),
        ("highest_vibration", "value_mm_s", "mm/s", "Highest vibration"),
        ("highest_current", "value_a", "A", "Highest motor current"),
    ]

    for key, value_key, unit, label in sensor_definitions:
        item = log_analysis.get(key)

        if isinstance(item, dict):
            value = item.get(value_key, "unavailable")
            timestamp = item.get("timestamp", "unknown time")
            lines.append(f"{label}: {value} {unit} at {timestamp}")
        else:
            lines.append(f"{label}: unavailable")

    trends = log_analysis.get("trends", {})

    if isinstance(trends, dict):
        lines.append("\nSENSOR TRENDS:")

        trend_definitions = [
            ("temperature_c", "Temperature", "°C"),
            ("vibration_mm_s", "Vibration", "mm/s"),
            ("motor_current_a", "Motor current", "A"),
        ]

        for key, label, unit in trend_definitions:
            trend = trends.get(key)

            if not isinstance(trend, dict):
                lines.append(f"{label}: trend unavailable")
                continue

            first = trend.get("first_value", "unavailable")
            latest = trend.get("latest_value", "unavailable")
            change = trend.get("change", "unavailable")
            direction = trend.get("direction", "unknown")

            lines.append(
                f"{label}: {first} to {latest} {unit}; "
                f"change: {change} {unit}; direction: {direction}"
            )

    intervals = log_analysis.get("interval_analysis", [])

    if isinstance(intervals, list):
        lines.append("\nCONSECUTIVE INTERVAL ANALYSIS:")

        for interval in intervals:
            if not isinstance(interval, dict):
                continue

            start = interval.get("from_timestamp", "unknown")
            end = interval.get("to_timestamp", "unknown")

            lines.append(
                f"{start} to {end}: "
                f"temperature change "
                f"{interval.get('temperature_change_c', 'unavailable')} °C; "
                f"vibration change "
                f"{interval.get('vibration_change_mm_s', 'unavailable')} mm/s; "
                f"current change "
                f"{interval.get('motor_current_change_a', 'unavailable')} A; "
                f"all three increased: "
                f"{interval.get('all_three_measurements_increased', 'unknown')}"
            )

    lines.append(
        "\nIntervals where all three measurements increased: "
        f"{log_analysis.get('simultaneous_increase_intervals', 'unavailable')}"
    )

    statuses = log_analysis.get("observed_statuses", [])

    if isinstance(statuses, list):
        lines.append(
            "Observed statuses: "
            + ", ".join(str(status) for status in statuses)
        )

    latest = log_analysis.get("latest_reading")

    if isinstance(latest, dict):
        lines.append("\nLATEST READING:")

        for key, value in latest.items():
            lines.append(f"{key}: {value}")

    lines.append(
        "\nEvidence limitation: Sensor trends and simultaneous increases "
        "do not independently confirm a specific root cause."
    )

    return "\n".join(lines)


# ============================================================
# 7. BUILD A FALLBACK INVESTIGATION REPORT
# ============================================================

def build_fallback_report(log_analysis, retrieved_sections):
    """Build a conservative report from logs and retrieved evidence."""

    non_safety_sections = [
        section
        for section in retrieved_sections
        if section.get("heading", "").strip().lower().rstrip(":") != "safety"
    ]

    manual_evidence = "\n\n".join(
        section.get("text", "").strip()
        for section in non_safety_sections
        if section.get("text", "").strip()
    )

    if not manual_evidence:
        manual_evidence = (
            "No non-safety troubleshooting section was retrieved. "
            "A manual-supported root cause cannot be identified from "
            "the available retrieved evidence."
        )

    safety_sections = [
        section
        for section in retrieved_sections
        if section.get("heading", "").strip().lower().rstrip(":") == "safety"
    ]

    safety_parts = []

    for section in safety_sections:
        text = section.get("text", "").strip()
        lines = text.splitlines()

        if lines and lines[0].strip().lower().rstrip(":") == "safety":
            text = "\n".join(lines[1:]).strip()

        if text:
            safety_parts.append(text)

    safety_text = "\n".join(safety_parts).strip()

    if not safety_text:
        safety_text = (
            "Disconnect and isolate electrical power before physical "
            "inspection. Follow applicable site lockout/tagout procedures "
            "and manufacturer safety instructions. Electrical inspections "
            "must be performed by qualified personnel."
        )

    trends = log_analysis.get("trends", {})

    if not isinstance(trends, dict):
        trends = {}

    intervals = log_analysis.get("interval_analysis", [])

    if not isinstance(intervals, list):
        intervals = []

    temperature = trends.get("temperature_c", {})
    vibration = trends.get("vibration_mm_s", {})
    current = trends.get("motor_current_a", {})

    if not isinstance(temperature, dict):
        temperature = {}

    if not isinstance(vibration, dict):
        vibration = {}

    if not isinstance(current, dict):
        current = {}

    trend_lines = [
        (
            "Temperature: "
            f"{temperature.get('first_value', 'unavailable')} to "
            f"{temperature.get('latest_value', 'unavailable')} °C; "
            f"change {temperature.get('change', 'unavailable')} °C."
        ),
        (
            "Vibration: "
            f"{vibration.get('first_value', 'unavailable')} to "
            f"{vibration.get('latest_value', 'unavailable')} mm/s; "
            f"change {vibration.get('change', 'unavailable')} mm/s."
        ),
        (
            "Motor current: "
            f"{current.get('first_value', 'unavailable')} to "
            f"{current.get('latest_value', 'unavailable')} A; "
            f"change {current.get('change', 'unavailable')} A."
        ),
    ]

    interval_lines = []

    for interval in intervals:
        if not isinstance(interval, dict):
            continue

        interval_lines.append(
            f"{interval.get('from_timestamp', 'unknown')} to "
            f"{interval.get('to_timestamp', 'unknown')}: "
            f"temperature change "
            f"{interval.get('temperature_change_c', 'unavailable')} °C, "
            f"vibration change "
            f"{interval.get('vibration_change_mm_s', 'unavailable')} mm/s, "
            f"current change "
            f"{interval.get('motor_current_change_a', 'unavailable')} A."
        )

    if not interval_lines:
        interval_lines.append(
            "Consecutive interval details are unavailable."
        )

    report = f"""
OBSERVED FACTS

{format_log_analysis(log_analysis)}

The readings describe observed conditions and do not independently
confirm a specific mechanical or electrical fault.

SENSOR TRENDS

{chr(10).join(trend_lines)}

CONSECUTIVE READING PATTERN

{chr(10).join(interval_lines)}

Simultaneous increases are an observed association, not proof of a
shared root cause.

POSSIBLE CAUSES

Retrieved manual evidence:
{manual_evidence}

The retrieved manual describes troubleshooting information, not proof
that a particular cause is present on this machine. Root cause not
confirmed; further inspection is required.

RECOMMENDED INSPECTIONS

1. Review the retrieved troubleshooting section and perform only the
   checks explicitly recommended there that apply to the observed fault.
   Do not infer a failed component or use unsupported inspection limits.

SAFETY

{safety_text}
""".strip()

    return clean_report_formatting(report)


# ============================================================
# 8. BASIC REPORT STRUCTURE VALIDATION
# ============================================================

def is_valid_report(report):
    """Validate required report sections and basic output quality."""

    if not isinstance(report, str):
        print("VALIDATION FAILED: Report is not a string.")
        return False

    report = report.strip()

    if len(report) < 250:
        print(
            f"VALIDATION FAILED: Report is too short "
            f"({len(report)} characters)."
        )
        return False

    required_headings = [
        "OBSERVED FACTS",
        "SENSOR TRENDS",
        "CONSECUTIVE READING PATTERN",
        "POSSIBLE CAUSES",
        "RECOMMENDED INSPECTIONS",
        "SAFETY",
    ]

    upper_report = report.upper()

    missing_headings = [
        heading
        for heading in required_headings
        if heading not in upper_report
    ]

    if missing_headings:
        print("VALIDATION FAILED: Missing headings:", missing_headings)
        return False

    heading_positions = [
        upper_report.find(heading)
        for heading in required_headings
    ]

    if heading_positions != sorted(heading_positions):
        print("VALIDATION FAILED: Required headings are out of order.")
        return False

    safety_position = upper_report.rfind("SAFETY")
    inspections_position = upper_report.find("RECOMMENDED INSPECTIONS")

    if safety_position < inspections_position:
        print("VALIDATION FAILED: Safety section is not at the end.")
        return False

    invalid_phrases = [
        "<think>",
        "</think>",
        "let me think",
        "i need to think",
    ]

    lower_report = report.lower()

    found_phrases = [
        phrase
        for phrase in invalid_phrases
        if phrase in lower_report
    ]

    if found_phrases:
        print(
            "VALIDATION FAILED: Internal reasoning markers found:",
            found_phrases,
        )
        return False

    incomplete_endings = [
        " this would",
        " because",
        " which may",
        " resulting in",
        " leading to",
        " and",
    ]

    if lower_report.endswith(tuple(incomplete_endings)):
        print("VALIDATION FAILED: Report may be incomplete.")
        return False

    print("VALIDATION PASSED: All report checks succeeded.")

    return True


# ============================================================
# 9. GENERATE THE AI INVESTIGATION REPORT
# ============================================================

def generate_investigation_report(
    machine_name,
    fault_description,
    log_analysis,
    retrieved_sections,
):
    """Generate an evidence-grounded report using Qwen."""

    manual_context = "\n\n".join(
        (
            f"SECTION: {section['heading']}\n"
            f"SIMILARITY: {section['similarity']}\n"
            f"CONTENT:\n{section['text']}"
        )
        for section in retrieved_sections
    )

    log_context = format_log_analysis(log_analysis)

    system_prompt = """
You are an industrial machine troubleshooting assistant.

Create a clear, accurate investigation report from the supplied
machine-log analysis and retrieved troubleshooting manual.

EVIDENCE-GROUNDING RULES:

1. OBSERVED FACTS:
   Use only values and events present in the supplied log analysis.
   Do not invent readings, dates, timestamps, or machine events.

2. SENSOR TRENDS:
   Report numerical changes only when supported by the supplied data.

3. CONSECUTIVE READING PATTERN:
   Use the supplied interval analysis when available.
   Simultaneous increases show an association, not proof of causation.

4. POSSIBLE CAUSES:
   List possible causes only when supported by the retrieved manual
   or clearly identified as general hypotheses requiring verification.

   For every cause, distinguish:
   - Manual-supported: the manual explicitly lists the cause.
   - Symptom match: observed symptoms are consistent with the cause.
   - Unconfirmed: available evidence does not establish the cause.

   Do not confuse a cause listed in the manual with proof that it caused
   this particular machine fault.

   Do not invent causal relationships between temperature, vibration,
   and current. Their simultaneous increase is an observed association,
   not proof of a shared cause.

   If the manual does not mention a proposed component, such as a gearbox,
   explicitly state that the manual does not support that component as
   a confirmed cause. Do not claim that the component is damaged.

5. RECOMMENDED INSPECTIONS:
   Ground recommendations in the retrieved manual.
   Do not invent manufacturer limits or inspection findings.
   Do not state that a component has failed without evidence.

6. ROOT CAUSE:
   When evidence is insufficient, explicitly state:
   "Root cause not confirmed; further inspection is required."

7. SAFETY:
   Preserve the retrieved manual's safety instructions.
   Follow electrical isolation and applicable lockout/tagout procedures
   before physical inspection. Electrical work must be performed
   by qualified personnel.

8. DATE AND TIME:
   Do not invent a report date. Use supplied log timestamps only
   when relevant to the investigation.

9. REQUIRED HEADINGS:
   Include these six headings in exactly this order:
   OBSERVED FACTS
   SENSOR TRENDS
   CONSECUTIVE READING PATTERN
   POSSIBLE CAUSES
   RECOMMENDED INSPECTIONS
   SAFETY

10. Keep the report concise and complete.
    Include no more than four possible causes and four inspections.
    Do not output hidden reasoning or <think> tags.
    State when information is unavailable.
    Finish with the SAFETY section and its practical instructions.

Use only the evidence provided in the user message and retrieved
manual sections. Do not present assumptions as measured facts.
"""

    user_prompt = f"""
Machine: {machine_name}

Fault description:
{fault_description}

MACHINE-LOG ANALYSIS:
{log_context}

RETRIEVED TROUBLESHOOTING MANUAL SECTIONS:
{manual_context}

Generate the complete investigation report.
Follow all system instructions and use only the supplied evidence.
"""

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        options={
            "temperature": 0.2,
            "num_predict": NUM_PREDICT,
        },
    )

    raw_report = response["message"]["content"].strip()

    print("\n--- RAW QWEN REPORT ---")
    print(raw_report)
    print("--- END RAW QWEN REPORT ---\n")

    # Apply the shared formatter exactly once.
    report = clean_report_formatting(raw_report)

    print("\n--- CLEANED QWEN REPORT ---")
    print(report)
    print("--- END CLEANED QWEN REPORT ---\n")

    if is_valid_report(report):
        return report, "qwen3"

    print(
        "WARNING: LLM report did not pass validation. "
        "Using the Python fallback report."
    )

    fallback_report = build_fallback_report(
        log_analysis,
        retrieved_sections,
    )

    # The fallback builder also uses the shared formatter.
    return fallback_report, "python_fallback"


# ============================================================
# 10. MAIN INVESTIGATION FUNCTION
# ============================================================

def investigate_machine_fault(
    machine_name,
    fault_description,
):
    """Run log analysis, RAG retrieval, and report generation."""

    print("\nDEBUG: Investigation function started")

    try:
        # A. Analyze the machine log.
        log_analysis = analyze_machine_logs()

        if not isinstance(log_analysis, dict):
            raise ValueError(
                "Machine-log analyzer did not return a dictionary."
            )

        if log_analysis.get("status") != "success":
            raise RuntimeError(
                "Machine-log analysis failed: "
                f"{log_analysis.get('error', 'Unknown error')}"
            )

        # B. Load the troubleshooting manual.
        chunks = load_manual_chunks()

        # C. Load or create document embeddings.
        document_embeddings = get_document_embeddings(chunks)

        # D. Retrieve relevant manual sections.
        retrieved_sections = retrieve_manual_sections(
            fault_description,
            chunks,
            document_embeddings,
        )

        # E. Generate the investigation report.
        report, report_source = generate_investigation_report(
            machine_name=machine_name,
            fault_description=fault_description,
            log_analysis=log_analysis,
            retrieved_sections=retrieved_sections,
        )

        # F. Validate the report against logs and manual evidence.
        evidence_validation = validate_report_evidence(
            report=report,
            log_analysis=log_analysis,
            retrieved_sections=retrieved_sections,
        )

        print("\n--- REPORT EVIDENCE VALIDATION ---")
        print(evidence_validation)

        safety_included = any(
            section["heading"].strip().lower().rstrip(":") == "safety"
            for section in retrieved_sections
        )

        evidence_check_passed = (
            isinstance(evidence_validation, dict)
            and evidence_validation.get("evidence_check_passed") is True
        )

        evidence_issues = (
            evidence_validation.get(
                "evidence_issues",
                ["Evidence validator returned an unexpected result."],
            )
            if isinstance(evidence_validation, dict)
            else ["Evidence validator returned an unexpected result."]
        )

        investigation_status = (
            "success" if evidence_check_passed else "validation_failed"
        )

        result = {
            "status": investigation_status,
            "machine_name": machine_name,
            "fault_description": fault_description,
            "report_source": report_source,
            "log_analysis": log_analysis,
            "retrieved_sections": retrieved_sections,
            "safety_instructions_included": safety_included,
            "report": report,
            "evidence_check_passed": evidence_check_passed,
            "evidence_issues": evidence_issues,
        }

        if not evidence_check_passed:
            result["message"] = (
                "The investigation pipeline completed, but the report did "
                "not pass evidence validation. Review evidence_issues before "
                "using or presenting this report."
            )

        return result

    except Exception as error:
        print("ERROR: Machine investigation failed:", str(error))

        return {
            "status": "error",
            "machine_name": machine_name,
            "fault_description": fault_description,
            "error": str(error),
            "message": (
                "The investigation could not be completed. "
                "Check the backend terminal for details."
            ),
        }
