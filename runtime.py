"""Configure privacy and SQLite compatibility before importing CrewAI."""
import os
import sys


def configure_runtime() -> None:
    os.environ["OTEL_SDK_DISABLED"] = "true"
    os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
    import sqlite3
    if sqlite3.sqlite_version_info < (3, 35, 0):
        try:
            import pysqlite3
        except ImportError as exc:
            raise RuntimeError(
                "SQLite 3.35+ is required. Install pysqlite3-binary on Linux "
                "or use a Python build with a newer SQLite."
            ) from exc
        sys.modules["sqlite3"] = pysqlite3
