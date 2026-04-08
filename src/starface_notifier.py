"""Starface phone system integration -- logs inbound calls and notifies internal users."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def load_internal_users(config_path: Path | None = None) -> dict[str, tuple[str, str]]:
    """Load internal user mapping from JSON config.

    Returns a dict mapping extension number to (display_name, windows_username).
    """
    if config_path is None:
        config_path = Path(__file__).resolve().parent.parent / "config" / "internal_users.json"

    with config_path.open(encoding="utf-8") as f:
        raw: dict[str, dict[str, str]] = json.load(f)

    return {ext: (data["name"], data["username"]) for ext, data in raw.items()}


def is_internal_call(caller_id: str, users: dict[str, tuple[str, str]]) -> bool:
    """Check if the caller ID belongs to a known internal extension."""
    return caller_id in users


def lookup_contact(csv_path: Path, phone_number: str) -> tuple[str, str]:
    """Search contacts CSV for an exact phone number match.

    Returns (full_name, company) or ("", "") if not found.
    """
    if not csv_path.exists():
        return "", ""

    with csv_path.open(encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=";")
        for row in reader:
            if len(row) >= 4 and row[3].strip() == phone_number:
                full_name = f"{row[0].strip()} {row[1].strip()}"
                company = row[2].strip()
                return full_name, company

    return "", ""


def create_call_log(
    log_dir: Path,
    caller_id: str,
    contact_name: str,
    company: str,
    timestamp: datetime,
) -> Path:
    """Create a call log file in a date-based directory structure.

    Returns the path to the created file.
    """
    date_dir = log_dir / timestamp.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)

    filename = timestamp.strftime("%H-%M-%S__") + caller_id + "__.txt"
    filepath = date_dir / filename

    filepath.write_text(
        f"Datum: {timestamp.strftime('%Y-%m-%d')}\n"
        f"Uhrzeit: {timestamp.strftime('%H:%M:%S')}\n\n"
        f"Anrufnummer: {caller_id}\n"
        f"Firma: {company}\n"
        f"Name: {contact_name}\n"
        f"Anliegen: \n\n\n",
        encoding="utf-8",
    )

    return filepath


def send_internal_message(username: str, display_name: str) -> None:
    """Send a Windows popup message to an internal user via msg command."""
    subprocess.run(  # noqa: S603
        ["msg", username, f"Moin {display_name} Du stinkst! <3"],  # noqa: S607
        check=True,
        timeout=10,
    )


def main(argv: list[str] | None = None) -> int:
    """Main entry point. Accepts optional argv for testability."""
    args = argv if argv is not None else sys.argv[1:]

    if len(args) != 1:
        print("Usage: Starface_Notizen.py <caller_id>", file=sys.stderr)
        return 1

    caller_id = args[0]
    if not caller_id.isdigit():
        print(f"Ungueltige Rufnummer: {caller_id!r}", file=sys.stderr)
        return 1

    base_dir = Path(__file__).resolve().parent.parent
    internal_users = load_internal_users()

    if is_internal_call(caller_id, internal_users):
        display_name, windows_username = internal_users[caller_id]
        try:
            send_internal_message(windows_username, display_name)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            print(f"Nachricht konnte nicht gesendet werden: {e}", file=sys.stderr)
            return 1
    else:
        timestamp = datetime.now()
        csv_path = base_dir / "contacts.csv"
        contact_name, company = lookup_contact(csv_path, caller_id)
        filepath = create_call_log(base_dir, caller_id, contact_name, company, timestamp)

        try:
            os.startfile(filepath)  # noqa: S606
        except OSError as e:
            print(f"Datei konnte nicht geoeffnet werden: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
