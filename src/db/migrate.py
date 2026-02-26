from __future__ import annotations

import argparse
import importlib
import pkgutil

from src.db.sqlite_client import get_connection


def _is_postgres(conn: object) -> bool:
    return conn.__class__.__module__.startswith("psycopg")


def ensure_migrations_table(conn: object) -> None:
    if _is_postgres(conn):
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
    conn.commit()


def applied_migration_names(conn: object) -> set[str]:
    cur = conn.cursor() if _is_postgres(conn) else conn
    rows = cur.execute("SELECT name FROM _migrations").fetchall()
    return {row[0] for row in rows}


def discover_migrations() -> list[str]:
    package_name = "migrations"
    modules = [name for _, name, _ in pkgutil.iter_modules([package_name]) if name[0:3].isdigit()]
    return sorted(modules)


def apply_all(db_path: str) -> None:
    conn = get_connection(db_path)
    ensure_migrations_table(conn)
    already = applied_migration_names(conn)
    for module_name in discover_migrations():
        if module_name in already:
            continue
        mod = importlib.import_module(f"migrations.{module_name}")
        mod.up(conn)
        cur = conn.cursor() if _is_postgres(conn) else conn
        if _is_postgres(conn):
            cur.execute("INSERT INTO _migrations(name) VALUES (%s)", (module_name,))
        else:
            cur.execute("INSERT INTO _migrations(name) VALUES (?)", (module_name,))
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="data/yescount.db")
    args = parser.parse_args()
    apply_all(args.db_path)


if __name__ == "__main__":
    main()
