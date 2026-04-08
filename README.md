# Python_Arbeit

Utility-Skripte fuer die Arbeit: OpenVPN Config Builder und Starface Telefon-Integration.

## Skripte

### ovpn.py - OpenVPN Config Builder
Erstellt fertige `.ovpn`-Dateien aus PKCS12-Zertifikaten. Extrahiert Zertifikat und Private Key aus `.p12`-Dateien und baut sie zusammen mit einem Root-Zertifikat in eine OpenVPN-Konfiguration ein.

```bash
python ovpn.py
```

Benoetigt: `.ovpn`-Template, `.p12`-Datei, `root.key` im Projektverzeichnis.

### Starface_Notizen.py - Anruf-Logger
Integration fuer die Starface-Telefonanlage. Loggt eingehende Anrufe in Textdateien und benachrichtigt interne Benutzer per Windows-Popup.

```bash
python Starface_Notizen.py <rufnummer>
```

In Starface konfigurieren mit: `c:\Users\<username>\Starface_anrufe\anrufe.py $(callerid)`

## Setup

```bash
# Abhaengigkeiten installieren
pip install -e .

# Entwicklungs-Abhaengigkeiten (Tests, Linting, Type-Checking)
pip install -e ".[dev]"
```

## Tests

```bash
# Tests ausfuehren
pytest

# Mit Coverage-Report
pytest --cov=src --cov-report=term-missing

# Linting
ruff check src/ tests/

# Type-Checking
mypy src/ --strict
```

## Konfiguration

Interne Benutzer-Zuordnung (Extension → Windows-User) in `config/internal_users.json`.
