#!/usr/bin/env python3
"""This python script will analyze and help you organize an Optimum mailbox using secure IMAP.

Default mode is read-only. Any changes/updates to a Mailbox require the APPLY command
and your explicit confirmation. Passwords are never stored by this program, it will ask for your PW when executed.
"""

from __future__ import annotations

import argparse
import csv
import email
import getpass
import imaplib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from email.header import decode_header, make_header
from email.utils import parseaddr
from pathlib import Path


DEFAULT_HOST = "mail.optimum.net"
DEFAULT_PORT = 993


@dataclass(frozen=True)
class MessageInfo:
    uid: str
    sender: str
    sender_email: str
    subject: str
    date: str


def decode(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except (LookupError, UnicodeDecodeError):
        return value


def connect(username: str, host: str, port: int) -> imaplib.IMAP4_SSL:
    password = os.environ.get("OPTIMUM_EMAIL_PASSWORD") or getpass.getpass(
        "Optimum email password (not saved): "
    )
    client = imaplib.IMAP4_SSL(host, port)
    client.login(username, password)
    return client


def load_rules(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    rules = data.get("rules")
    if not isinstance(rules, list):
        raise ValueError("Rules file must contain a 'rules' array.")
    for index, rule in enumerate(rules, start=1):
        if rule.get("action") not in {"move", "delete", "keep"}:
            raise ValueError(f"Rule {index} has an invalid action.")
        if rule["action"] == "move" and not rule.get("folder"):
            raise ValueError(f"Rule {index} is missing its destination folder.")
    return rules


def field_matches(value: str, condition: dict) -> bool:
    value = value.casefold()
    if "equals" in condition:
        return value == str(condition["equals"]).casefold()
    if "contains" in condition:
        return str(condition["contains"]).casefold() in value
    if "ends_with" in condition:
        return value.endswith(str(condition["ends_with"]).casefold())
    if "regex" in condition:
        return re.search(str(condition["regex"]), value, re.IGNORECASE) is not None
    raise ValueError("A match condition must use equals, contains, ends_with, or regex.")


def choose_rule(message: MessageInfo, rules: list[dict]) -> dict | None:
    values = {
        "sender": message.sender,
        "sender_email": message.sender_email,
        "subject": message.subject,
    }
    for rule in rules:
        conditions = rule.get("match", {})
        if conditions and all(
            name in values and field_matches(values[name], condition)
            for name, condition in conditions.items()
        ):
            return rule
    return None


def read_messages(client: imaplib.IMAP4_SSL, mailbox: str) -> list[MessageInfo]:
    status, _ = client.select(mailbox, readonly=True)
    if status != "OK":
        raise RuntimeError(f"Could not open mailbox: {mailbox}")
    status, data = client.uid("search", None, "ALL")
    if status != "OK":
        raise RuntimeError("Could not list messages.")

    messages: list[MessageInfo] = []
    for raw_uid in data[0].split():
        uid = raw_uid.decode("ascii")
        status, parts = client.uid(
            "fetch", uid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
        )
        if status != "OK" or not parts or not isinstance(parts[0], tuple):
            continue
        header = email.message_from_bytes(parts[0][1])
        sender = decode(header.get("From"))
        messages.append(
            MessageInfo(
                uid=uid,
                sender=sender,
                sender_email=parseaddr(sender)[1].casefold(),
                subject=decode(header.get("Subject")),
                date=header.get("Date", ""),
            )
        )
    return messages


def make_plan(messages: list[MessageInfo], rules: list[dict]) -> list[dict]:
    plan = []
    for message in messages:
        rule = choose_rule(message, rules)
        plan.append(
            {
                "uid": message.uid,
                "date": message.date,
                "sender": message.sender,
                "sender_email": message.sender_email,
                "subject": message.subject,
                "rule": rule.get("name", "") if rule else "",
                "action": rule.get("action", "none") if rule else "none",
                "destination": rule.get("folder", "") if rule else "",
            }
        )
    return plan


def write_plan(plan: list[dict], output: Path) -> None:
    fields = [
        "uid", "date", "sender", "sender_email", "subject",
        "rule", "action", "destination",
    ]
    with output.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(plan)


def quote_mailbox(name: str) -> str:
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def ensure_folder(client: imaplib.IMAP4_SSL, folder: str) -> None:
    status, _ = client.create(quote_mailbox(folder))
    if status not in {"OK", "NO"}:  # NO commonly means it already exists.
        raise RuntimeError(f"Could not create or access folder: {folder}")


def move_uid(client: imaplib.IMAP4_SSL, uid: str, folder: str) -> None:
    ensure_folder(client, folder)
    status, _ = client.uid("COPY", uid, quote_mailbox(folder))
    if status != "OK":
        raise RuntimeError(f"Could not copy UID {uid} to {folder}.")
    status, _ = client.uid("STORE", uid, "+FLAGS.SILENT", "(\\Deleted)")
    if status != "OK":
        raise RuntimeError(f"Copied UID {uid}, but could not mark the original for removal.")


def apply_plan(
    client: imaplib.IMAP4_SSL, mailbox: str, plan: list[dict], trash: str
) -> dict[str, int]:
    status, _ = client.select(mailbox, readonly=False)
    if status != "OK":
        raise RuntimeError(f"Could not open mailbox for changes: {mailbox}")
    counts = {"move": 0, "delete": 0, "keep": 0, "none": 0, "errors": 0}
    for row in plan:
        action = row["action"]
        try:
            if action == "move":
                move_uid(client, row["uid"], row["destination"])
            elif action == "delete":
                move_uid(client, row["uid"], trash)
            counts[action] += 1
        except Exception as exc:  # Continue so one malformed message does not stop the run.
            counts["errors"] += 1
            print(f"UID {row['uid']}: {exc}", file=sys.stderr)
    client.expunge()
    return counts


def init_rules(path: Path) -> None:
    example = {
        "rules": [
            {
                "name": "Move store receipts",
                "match": {"sender_email": {"equals": "receipts@example.com"}},
                "action": "move",
                "folder": "Receipts",
            },
            {
                "name": "Delete old newsletter",
                "match": {
                    "sender_email": {"ends_with": "@newsletter.example"},
                    "subject": {"contains": "daily update"},
                },
                "action": "delete",
            },
            {
                "name": "Protect important mail",
                "match": {"subject": {"contains": "tax document"}},
                "action": "keep",
            },
        ]
    }
    path.write_text(json.dumps(example, indent=2) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--username", default=os.environ.get("OPTIMUM_EMAIL"))
    result.add_argument("--host", default=DEFAULT_HOST)
    result.add_argument("--port", type=int, default=DEFAULT_PORT)
    result.add_argument("--mailbox", default="INBOX")
    sub = result.add_subparsers(dest="command", required=True)

    initialize = sub.add_parser("init-rules", help="Create an example rules file")
    initialize.add_argument("--rules", type=Path, default=Path("email_rules.json"))

    analyze = sub.add_parser("analyze", help="Create a read-only CSV action preview")
    analyze.add_argument("--rules", type=Path, default=Path("email_rules.json"))
    analyze.add_argument("--output", type=Path)

    apply = sub.add_parser("apply", help="Apply the rules after confirmation")
    apply.add_argument("--rules", type=Path, default=Path("email_rules.json"))
    apply.add_argument("--trash", default="Trash")
    apply.add_argument("--yes", action="store_true", help="Skip the typed confirmation")
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "init-rules":
        if args.rules.exists():
            print(f"Refusing to overwrite existing file: {args.rules}", file=sys.stderr)
            return 2
        init_rules(args.rules)
        print(f"Created {args.rules}")
        return 0
    if not args.username:
        print("Provide --username or set OPTIMUM_EMAIL.", file=sys.stderr)
        return 2

    rules = load_rules(args.rules)
    client = connect(args.username, args.host, args.port)
    try:
        messages = read_messages(client, args.mailbox)
        plan = make_plan(messages, rules)
        counts = {action: sum(row["action"] == action for row in plan)
                  for action in ("move", "delete", "keep", "none")}
        if args.command == "analyze":
            output = args.output or Path(
                f"optimum_email_plan_{datetime.now():%Y%m%d_%H%M%S}.csv"
            )
            write_plan(plan, output)
            print(f"Analyzed {len(plan)} messages. Plan: {output}")
            print(json.dumps(counts, indent=2))
            return 0

        print("Planned actions:", json.dumps(counts, indent=2))
        if not args.yes:
            answer = input("Type APPLY to move these messages (deletes go to Trash): ")
            if answer != "APPLY":
                print("No mailbox changes made.")
                return 1
        results = apply_plan(client, args.mailbox, plan, args.trash)
        print("Completed:", json.dumps(results, indent=2))
        return 0 if results["errors"] == 0 else 1
    finally:
        try:
            client.logout()
        except imaplib.IMAP4.error:
            pass


if __name__ == "__main__":
    raise SystemExit(main())