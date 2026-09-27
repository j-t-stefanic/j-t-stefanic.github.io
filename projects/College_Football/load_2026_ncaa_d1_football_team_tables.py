#!/usr/bin/env python3
"""Load the 2026 NCAA Division I team-table SQL script into MySQL."""

from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path
from typing import Iterator

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    print(
        "Missing dependency: mysql-connector-python\n"
        "Install it with: python -m pip install mysql-connector-python",
        file=sys.stderr,
    )
    raise SystemExit(1)


DEFAULT_SQL_FILE = Path(__file__).with_name(
    "2026_ncaa_d1_football_team_tables_mysql.sql"
)


def sql_statements(sql_text: str) -> Iterator[str]:
    """Yield semicolon-terminated statements without splitting quoted values."""
    statement: list[str] = []
    quote: str | None = None
    in_line_comment = False
    in_block_comment = False
    index = 0

    while index < len(sql_text):
        char = sql_text[index]
        next_char = sql_text[index + 1] if index + 1 < len(sql_text) else ""

        if in_line_comment:
            if char == "\n":
                in_line_comment = False
                statement.append(char)
            index += 1
            continue

        if in_block_comment:
            if char == "*" and next_char == "/":
                in_block_comment = False
                index += 2
            else:
                index += 1
            continue

        if quote is None:
            if char == "#" or (char == "-" and next_char == "-"):
                in_line_comment = True
                index += 2 if char == "-" else 1
                continue
            if char == "/" and next_char == "*":
                in_block_comment = True
                index += 2
                continue
            if char in ("'", '"', "`"):
                quote = char
                statement.append(char)
            elif char == ";":
                completed = "".join(statement).strip()
                if completed:
                    yield completed
                statement.clear()
            else:
                statement.append(char)
            index += 1
            continue

        statement.append(char)

        if char == "\\" and quote in ("'", '"') and next_char:
            statement.append(next_char)
            index += 2
            continue

        if char == quote:
            if next_char == quote:
                statement.append(next_char)
                index += 2
                continue
            quote = None

        index += 1

    completed = "".join(statement).strip()
    if completed:
        yield completed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create and populate the 2026 NCAA Division I MySQL tables."
    )
    parser.add_argument(
        "--sql-file",
        type=Path,
        default=DEFAULT_SQL_FILE,
        help=f"SQL file to execute (default: {DEFAULT_SQL_FILE.name})",
    )
    parser.add_argument("--host", default="localhost", help="MySQL host")
    parser.add_argument("--port", type=int, default=3306, help="MySQL port")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sql_file = args.sql_file.expanduser().resolve()

    if not sql_file.is_file():
        print(f"SQL file not found: {sql_file}", file=sys.stderr)
        return 1

    username = input("MySQL username [root]: ").strip() or "root"
    password = getpass.getpass("MySQL password: ")

    connection = None
    cursor = None
    statement_number = 0

    try:
        print(f"Connecting to MySQL at {args.host}:{args.port}...")
        connection = mysql.connector.connect(
            host=args.host,
            port=args.port,
            user=username,
            password=password,
            charset="utf8mb4",
            autocommit=True,
        )
        cursor = connection.cursor()

        sql_text = sql_file.read_text(encoding="utf-8")
        print(f"Executing {sql_file.name}...")

        for statement_number, statement in enumerate(sql_statements(sql_text), start=1):
            cursor.execute(statement)
            if statement_number % 50 == 0:
                print(f"  Completed {statement_number} statements...")

        print(
            f"Import complete: {statement_number} SQL statements executed.\n"
            "Database: college_football_data"
        )
        return 0

    except (MySQLError, OSError, UnicodeError) as error:
        if connection is not None and connection.in_transaction:
            connection.rollback()
        location = (
            f"statement {statement_number}"
            if statement_number
            else "the MySQL connection"
        )
        print(f"Import failed at {location}: {error}", file=sys.stderr)
        return 1
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
