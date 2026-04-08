"""Tests for src.starface_notifier."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from src.starface_notifier import (
    create_call_log,
    is_internal_call,
    load_internal_users,
    lookup_contact,
    main,
    send_internal_message,
)

# --- load_internal_users tests ---


class TestLoadInternalUsers:
    def test_loads_config(self, internal_users_config: Path) -> None:
        users = load_internal_users(internal_users_config)

        assert "10" in users
        assert users["10"] == ("Peter", "ppeter")
        assert "20" in users
        assert users["20"] == ("hasen", "hhansen")

    def test_missing_config(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_internal_users(tmp_path / "nonexistent.json")


# --- is_internal_call tests ---


class TestIsInternalCall:
    def test_known_extension(self) -> None:
        users = {"10": ("Peter", "ppeter"), "20": ("hasen", "hhansen")}
        assert is_internal_call("10", users) is True

    def test_unknown_extension(self) -> None:
        users = {"10": ("Peter", "ppeter")}
        assert is_internal_call("99", users) is False

    def test_external_number(self) -> None:
        users = {"10": ("Peter", "ppeter")}
        assert is_internal_call("01234567890", users) is False


# --- lookup_contact tests ---


class TestLookupContact:
    def test_found(self, sample_contacts_csv: Path) -> None:
        name, company = lookup_contact(sample_contacts_csv, "+491234567890")
        assert name == "Mueller Hans"
        assert company == "ACME GmbH"

    def test_not_found(self, sample_contacts_csv: Path) -> None:
        name, company = lookup_contact(sample_contacts_csv, "+4900000000000")
        assert name == ""
        assert company == ""

    def test_no_substring_match(self, sample_contacts_csv: Path) -> None:
        """Ensure partial number matches do not return false positives."""
        name, company = lookup_contact(sample_contacts_csv, "1234567890")
        assert name == ""
        assert company == ""

    def test_missing_csv(self, tmp_path: Path) -> None:
        name, company = lookup_contact(tmp_path / "missing.csv", "123")
        assert name == ""
        assert company == ""

    def test_german_umlauts(self, sample_contacts_csv: Path) -> None:
        name, company = lookup_contact(sample_contacts_csv, "+4917612345678")
        assert name == "Böhm Klaus"
        assert company == "Bar KG"

    def test_empty_csv(self, tmp_path: Path) -> None:
        csv_file = tmp_path / "contacts.csv"
        csv_file.write_text("", encoding="utf-8")
        name, company = lookup_contact(csv_file, "+491234567890")
        assert name == ""
        assert company == ""

    def test_malformed_csv_line(self, tmp_path: Path) -> None:
        """Lines with fewer than 4 fields should be skipped."""
        csv_file = tmp_path / "contacts.csv"
        csv_file.write_text("incomplete;row\n", encoding="utf-8")
        name, company = lookup_contact(csv_file, "row")
        assert name == ""
        assert company == ""


# --- create_call_log tests ---


class TestCreateCallLog:
    def test_creates_directory_and_file(self, tmp_path: Path) -> None:
        timestamp = datetime(2026, 4, 8, 14, 30, 45)
        filepath = create_call_log(tmp_path, "01234567890", "Hans Mueller", "ACME GmbH", timestamp)

        assert filepath.exists()
        assert filepath.parent.name == "2026-04-08"
        assert filepath.name == "14-30-45__01234567890__.txt"

    def test_file_content(self, tmp_path: Path) -> None:
        timestamp = datetime(2026, 4, 8, 14, 30, 45)
        filepath = create_call_log(tmp_path, "01234567890", "Hans Mueller", "ACME GmbH", timestamp)

        content = filepath.read_text(encoding="utf-8")
        assert "Datum: 2026-04-08" in content
        assert "Uhrzeit: 14:30:45" in content
        assert "Anrufnummer: 01234567890" in content
        assert "Firma: ACME GmbH" in content
        assert "Name: Hans Mueller" in content
        assert "Anliegen:" in content

    def test_existing_directory(self, tmp_path: Path) -> None:
        """Should not fail if the date directory already exists."""
        timestamp = datetime(2026, 4, 8, 10, 0, 0)
        (tmp_path / "2026-04-08").mkdir()

        filepath = create_call_log(tmp_path, "123", "", "", timestamp)
        assert filepath.exists()


# --- send_internal_message tests ---


class TestSendInternalMessage:
    def test_calls_subprocess(self) -> None:
        with patch("src.starface_notifier.subprocess.run") as mock_run:
            send_internal_message("ppeter", "Peter")

            mock_run.assert_called_once_with(
                ["msg", "ppeter", "Moin Peter Du stinkst! <3"],
                check=True,
                timeout=10,
            )


# --- main() tests ---


class TestMain:
    def test_no_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main([])
        assert result == 1
        assert "Usage" in capsys.readouterr().err

    def test_invalid_caller_id(self, capsys: pytest.CaptureFixture[str]) -> None:
        result = main(["abc"])
        assert result == 1
        assert "Ungueltige" in capsys.readouterr().err

    def test_external_call(self, tmp_path: Path) -> None:
        with (
            patch("src.starface_notifier.load_internal_users", return_value={}),
            patch("src.starface_notifier.lookup_contact", return_value=("Hans Mueller", "ACME")),
            patch(
                "src.starface_notifier.create_call_log",
                return_value=tmp_path / "log.txt",
            ) as mock_log,
            patch("src.starface_notifier.os.startfile"),
        ):
            result = main(["01234567890"])
            assert result == 0
            mock_log.assert_called_once()

    def test_internal_call(self, internal_users_config: Path) -> None:
        with (
            patch(
                "src.starface_notifier.load_internal_users",
                return_value={"10": ("Peter", "ppeter")},
            ),
            patch("src.starface_notifier.send_internal_message") as mock_msg,
        ):
            result = main(["10"])
            assert result == 0
            mock_msg.assert_called_once_with("ppeter", "Peter")

    def test_unknown_internal_extension(self, tmp_path: Path) -> None:
        with (
            patch(
                "src.starface_notifier.load_internal_users",
                return_value={"10": ("Peter", "ppeter")},
            ),
            patch("src.starface_notifier.lookup_contact", return_value=("", "")),
            patch(
                "src.starface_notifier.create_call_log",
                return_value=tmp_path / "log.txt",
            ),
            patch("src.starface_notifier.os.startfile"),
        ):
            # Extension "99" is not in the user dict, so it's treated as external
            result = main(["99"])
            assert result == 0

    def test_message_failure(self, capsys: pytest.CaptureFixture[str]) -> None:
        import subprocess

        with (
            patch(
                "src.starface_notifier.load_internal_users",
                return_value={"10": ("Peter", "ppeter")},
            ),
            patch(
                "src.starface_notifier.send_internal_message",
                side_effect=subprocess.CalledProcessError(1, "msg"),
            ),
        ):
            result = main(["10"])
            assert result == 1
            assert "Nachricht" in capsys.readouterr().err
