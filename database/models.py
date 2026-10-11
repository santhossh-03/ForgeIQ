
import json
from pathlib import Path

from database.connection import DATABASE_PATH, get_connection


def save_investigation(result, db_path=DATABASE_PATH):
    """Save an investigation result and return its database ID."""

    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO investigations (
                machine_name,
                fault_description,
                status,
                report_source,
                log_analysis,
                retrieved_sections,
                safety_instructions_included,
                report,
                evidence_check_passed,
                evidence_issues,
                message,
                error
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result["machine_name"],
                result["fault_description"],
                result["status"],
                result.get("report_source"),
                json.dumps(result.get("log_analysis")),
                json.dumps(result.get("retrieved_sections")),
                (
                    None
                    if result.get("safety_instructions_included") is None
                    else int(result["safety_instructions_included"])
                ),
                result.get("report"),
                (
                    None
                    if result.get("evidence_check_passed") is None
                    else int(result["evidence_check_passed"])
                ),
                json.dumps(result.get("evidence_issues", [])),
                result.get("message"),
                result.get("error"),
            ),
        )

        connection.commit()
        return cursor.lastrowid


def get_investigation(investigation_id, db_path=DATABASE_PATH):
    """Retrieve one investigation by its ID."""

    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM investigations
            WHERE id = ?
            """,
            (investigation_id,),
        ).fetchone()

    if row is None:
        return None

    return dict(row)


def list_investigations(limit=50, db_path=DATABASE_PATH):
    """Return the most recent investigations first."""

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")

    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                machine_name,
                fault_description,
                status,
                report_source,
                evidence_check_passed,
                created_at
            FROM investigations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]
