
import sqlite3
from contextlib import contextmanager
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "database" / "investigations.db"


@contextmanager
def get_connection(db_path=DATABASE_PATH):
    """Open a SQLite connection and always close it afterward."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(db_path=DATABASE_PATH):
    """Create the investigations table if it does not exist."""
    with get_connection(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_name TEXT NOT NULL,
                fault_description TEXT NOT NULL,
                status TEXT NOT NULL,
                report_source TEXT,
                log_analysis TEXT,
                retrieved_sections TEXT,
                safety_instructions_included INTEGER,
                report TEXT,
                evidence_check_passed INTEGER,
                evidence_issues TEXT NOT NULL DEFAULT '[]',
                message TEXT,
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
