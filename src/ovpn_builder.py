"""OpenVPN configuration builder -- embeds PKCS12 certificates into .ovpn files."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path

try:
    from cryptography.hazmat.primitives.serialization import (
        BestAvailableEncryption,
        Encoding,
        PrivateFormat,
        pkcs12,
    )
except ImportError:
    print("Fehlende Abhängigkeit: pip install cryptography", file=sys.stderr)
    sys.exit(1)


def safe_path(base_dir: Path, filename: str, suffix: str) -> Path:
    """Resolve a filename relative to base_dir, preventing directory traversal."""
    candidate = (base_dir / filename).with_suffix(suffix).resolve()
    if not candidate.is_relative_to(base_dir.resolve()):
        raise ValueError(f"Pfad-Traversal erkannt: {filename}")
    return candidate


def extract_pkcs12(p12_path: Path, password: str) -> tuple[str, str]:
    """Decrypt a PKCS12 file and return (cert_pem, key_pem) as strings."""
    pkcs12_data = p12_path.read_bytes()
    password_bytes = password.encode("utf-8")

    private_key, certificate, _ = pkcs12.load_key_and_certificates(pkcs12_data, password_bytes)

    if certificate is None:
        raise ValueError("PKCS12-Datei enthaelt kein Zertifikat")
    if private_key is None:
        raise ValueError("PKCS12-Datei enthaelt keinen Private Key")

    cert_pem = certificate.public_bytes(Encoding.PEM).decode("ascii")
    key_pem = private_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.PKCS8,
        BestAvailableEncryption(password_bytes),
    ).decode("ascii")

    return cert_pem, key_pem


def build_ovpn(template_content: str, root_key_content: str, cert: str, key: str) -> str:
    """Assemble the final .ovpn file content from template, root key, cert, and private key."""
    return (
        template_content
        + "persist-key\npersist-tun\n"
        + f"<ca>\n{root_key_content}\n</ca>\n"
        + f"<cert>\n{cert}</cert>\n"
        + f"<key>\n{key}</key>"
    )


def write_ovpn(output_path: Path, content: str) -> None:
    """Write the assembled .ovpn content to a file."""
    output_path.write_text(content, encoding="utf-8")


def main() -> int:
    """Interactive CLI: prompts for filenames and password, builds the .ovpn file."""
    base_dir = Path(__file__).resolve().parent.parent

    try:
        ovpn_name = input("Name der .ovpn Datei (ohne Endung): ")
        p12_name = input("Name der .p12 Datei (ohne Endung): ")
        password = getpass.getpass("Passwort: ")

        template_path = safe_path(base_dir, ovpn_name, ".ovpn")
        p12_path = safe_path(base_dir, p12_name, ".p12")
        root_key_path = base_dir / "root.key"

        if not template_path.exists():
            print(f"OVPN-Template nicht gefunden: {template_path}", file=sys.stderr)
            return 1
        if not p12_path.exists():
            print(f"PKCS12-Datei nicht gefunden: {p12_path}", file=sys.stderr)
            return 1
        if not root_key_path.exists():
            print(f"Root-Key nicht gefunden: {root_key_path}", file=sys.stderr)
            return 1

        template_content = template_path.read_text(encoding="utf-8")
        root_key_content = root_key_path.read_text(encoding="utf-8")

        cert, key = extract_pkcs12(p12_path, password)
        ovpn_content = build_ovpn(template_content, root_key_content, cert, key)

        output_path = safe_path(base_dir, p12_name + "_neu", ".ovpn")
        write_ovpn(output_path, ovpn_content)

        print(f"Erstellt: {output_path}")

    except ValueError as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
