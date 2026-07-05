import os
from pathlib import Path

import pymysql


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"


def get_db_config(include_database=True):
    config = {
        "host": os.getenv("AIRPLANE_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("AIRPLANE_DB_PORT", "3306")),
        "user": os.getenv("AIRPLANE_DB_USER", "root"),
        "password": os.getenv("AIRPLANE_DB_PASSWORD", ""),
        "charset": "utf8mb4",
        "autocommit": True,
        "cursorclass": pymysql.cursors.DictCursor,
    }
    if include_database:
        config["database"] = os.getenv("AIRPLANE_DB_NAME", "airplane_game")
    return config


def get_connection(include_database=True):
    return pymysql.connect(**get_db_config(include_database=include_database))


def init_database():
    db_name = os.getenv("AIRPLANE_DB_NAME", "airplane_game")

    with get_connection(include_database=False) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                "DEFAULT CHARACTER SET utf8mb4 "
                "DEFAULT COLLATE utf8mb4_unicode_ci"
            )

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]

    with get_connection(include_database=True) as conn:
        with conn.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)


if __name__ == "__main__":
    init_database()
    print("MySQL database initialized.")
