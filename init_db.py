"""Initialize the telecom operations SQLite database."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from utils.config import DATA_PATH, DB_PATH

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOGGER = logging.getLogger(__name__)


def _execute_script(cursor: sqlite3.Cursor, script_path: Path) -> None:
    """Execute one SQL script file with helpful error messages."""
    try:
        sql_text = script_path.read_text(encoding="utf-8")
        cursor.executescript(sql_text)
        LOGGER.info("Executed %s", script_path.name)
    except OSError as exc:
        raise RuntimeError(f"Failed to read SQL script {script_path}: {exc}") from exc
    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Failed to execute SQL script {script_path.name}: {exc}"
        ) from exc


def initialize_database() -> None:
    """Create sqlite database and run schema/seed scripts."""
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    sql_dir = Path(__file__).resolve().parent / "sql"
    scripts = [sql_dir / "01_schema.sql", sql_dir / "02_seed_data.sql"]

    try:
        connection = sqlite3.connect(DB_PATH)
        with connection:
            cursor = connection.cursor()
            for script in scripts:
                _execute_script(cursor, script)
    except sqlite3.Error as exc:
        raise RuntimeError(f"Database initialization failed: {exc}") from exc
    finally:
        if "connection" in locals():
            connection.close()


if __name__ == "__main__":
    initialize_database()
