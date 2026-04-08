"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def base_dir(tmp_path: Path) -> Path:
    """Provide a temporary base directory mimicking the project root."""
    return tmp_path


@pytest.fixture
def sample_contacts_csv(tmp_path: Path) -> Path:
    """Create a sample contacts.csv with German characters."""
    csv_content = (
        "Mueller;Hans;ACME GmbH;+491234567890\n"
        "Schmidt;Anna;Foo AG;+490987654321\n"
        "Böhm;Klaus;Bar KG;+4917612345678\n"
    )
    csv_file = tmp_path / "contacts.csv"
    csv_file.write_text(csv_content, encoding="utf-8")
    return csv_file


@pytest.fixture
def internal_users_config(tmp_path: Path) -> Path:
    """Create a test internal users JSON config."""
    config = {
        "10": {"name": "Peter", "username": "ppeter"},
        "20": {"name": "hasen", "username": "hhansen"},
    }
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_path = config_dir / "internal_users.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path
