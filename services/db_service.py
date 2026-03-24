from __future__ import annotations

import logging
import sqlite3
from typing import Any

from config.settings import GRAFANA_SQLITE_PATH
from helpers.decorators import db_error_handler


class GrafanaSqliteUserRepository:
    """只读访问 Grafana SQLite，用于测试校验。"""

    @staticmethod
    @db_error_handler
    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(GRAFANA_SQLITE_PATH, timeout=5)
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.row_factory = sqlite3.Row
        logging.info("Connected to %s", GRAFANA_SQLITE_PATH)
        return connection

    @staticmethod
    def _normalize_user_row(row: sqlite3.Row | None) -> tuple[str, str, str, int] | None:
        if row is None:
            return None
        return (row["login"], row["email"], row["name"], row["id"])

    @staticmethod
    @db_error_handler
    def find_user_by_login(login: str) -> tuple[str, str, str, int] | None:
        with GrafanaSqliteUserRepository.connect() as connection:
            cursor = connection.execute(
                "SELECT login, email, name, id FROM user WHERE login = ? ORDER BY id DESC LIMIT 1",
                (login,),
            )
            return GrafanaSqliteUserRepository._normalize_user_row(cursor.fetchone())

    @staticmethod
    @db_error_handler
    def find_user_by_email(email: str) -> tuple[str, str, str, int] | None:
        with GrafanaSqliteUserRepository.connect() as connection:
            cursor = connection.execute(
                "SELECT login, email, name, id FROM user WHERE email = ? ORDER BY id DESC LIMIT 1",
                (email,),
            )
            return GrafanaSqliteUserRepository._normalize_user_row(cursor.fetchone())


# backward compatibility
DBService = GrafanaSqliteUserRepository
