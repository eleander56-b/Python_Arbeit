"""Tests for src.ovpn_builder."""

from __future__ import annotations

import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
    pkcs12,
)

from src.ovpn_builder import build_ovpn, extract_pkcs12, main, safe_path, write_ovpn

# --- Helpers ---


def create_test_p12(path: Path, password: bytes) -> tuple[str, str]:
    """Create a minimal PKCS12 file for testing. Returns (cert_pem, key_pem)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )

    p12_data = pkcs12.serialize_key_and_certificates(
        name=b"test",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=BestAvailableEncryption(password),
    )
    path.write_bytes(p12_data)

    cert_pem = cert.public_bytes(Encoding.PEM).decode("ascii")
    key_pem = key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, BestAvailableEncryption(password)
    ).decode("ascii")
    return cert_pem, key_pem


# --- safe_path tests ---


class TestSafePath:
    def test_valid_filename(self, tmp_path: Path) -> None:
        result = safe_path(tmp_path, "myfile", ".ovpn")
        assert result == (tmp_path / "myfile.ovpn").resolve()
        assert result.suffix == ".ovpn"

    def test_traversal_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Pfad-Traversal"):
            safe_path(tmp_path, "../../etc/passwd", ".ovpn")

    def test_relative_traversal_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Pfad-Traversal"):
            safe_path(tmp_path, "../outside", ".p12")

    def test_simple_name(self, tmp_path: Path) -> None:
        result = safe_path(tmp_path, "test", ".p12")
        assert result.name == "test.p12"
        assert result.parent == tmp_path.resolve()


# --- extract_pkcs12 tests ---


class TestExtractPkcs12:
    def test_valid_extraction(self, tmp_path: Path) -> None:
        p12_path = tmp_path / "test.p12"
        password = "testpass"
        create_test_p12(p12_path, password.encode("utf-8"))

        cert, key = extract_pkcs12(p12_path, password)

        assert "BEGIN CERTIFICATE" in cert
        assert "END CERTIFICATE" in cert
        assert "BEGIN ENCRYPTED PRIVATE KEY" in key

    def test_wrong_password(self, tmp_path: Path) -> None:
        p12_path = tmp_path / "test.p12"
        create_test_p12(p12_path, b"correctpass")

        with pytest.raises(ValueError, match="Invalid password"):
            extract_pkcs12(p12_path, "wrongpass")

    def test_missing_file(self, tmp_path: Path) -> None:
        p12_path = tmp_path / "nonexistent.p12"

        with pytest.raises(FileNotFoundError):
            extract_pkcs12(p12_path, "anypass")


# --- build_ovpn tests ---


class TestBuildOvpn:
    def test_assembly(self) -> None:
        template = "client\nremote server 1194\n"
        root_key = "ROOT_CA_CONTENT"
        cert = "CERT_CONTENT\n"
        key = "KEY_CONTENT\n"

        result = build_ovpn(template, root_key, cert, key)

        assert result.startswith("client\nremote server 1194\n")
        assert "persist-key\npersist-tun\n" in result

    def test_contains_all_sections(self) -> None:
        result = build_ovpn("template\n", "root", "cert\n", "key\n")

        assert "<ca>" in result
        assert "</ca>" in result
        assert "<cert>" in result
        assert "</cert>" in result
        assert "<key>" in result
        assert "</key>" in result

    def test_root_key_in_ca_section(self) -> None:
        result = build_ovpn("", "MY_ROOT_KEY", "cert\n", "key\n")
        ca_start = result.index("<ca>")
        ca_end = result.index("</ca>")
        ca_section = result[ca_start:ca_end]
        assert "MY_ROOT_KEY" in ca_section


# --- write_ovpn tests ---


class TestWriteOvpn:
    def test_writes_content(self, tmp_path: Path) -> None:
        output = tmp_path / "output.ovpn"
        write_ovpn(output, "test content")
        assert output.read_text(encoding="utf-8") == "test content"


# --- Integration test ---


class TestEndToEnd:
    def test_full_pipeline(self, tmp_path: Path) -> None:
        """Test the entire flow: extract → build → write."""
        password = "testpass"
        p12_path = tmp_path / "user.p12"
        create_test_p12(p12_path, password.encode("utf-8"))

        template_path = tmp_path / "config.ovpn"
        template_path.write_text("client\n", encoding="utf-8")

        root_key_path = tmp_path / "root.key"
        root_key_path.write_text("ROOT_CA\n", encoding="utf-8")

        cert, key = extract_pkcs12(p12_path, password)
        template_content = template_path.read_text(encoding="utf-8")
        root_key_content = root_key_path.read_text(encoding="utf-8")
        ovpn_content = build_ovpn(template_content, root_key_content, cert, key)

        output_path = tmp_path / "user_neu.ovpn"
        write_ovpn(output_path, ovpn_content)

        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "client" in content
        assert "<ca>" in content
        assert "ROOT_CA" in content
        assert "<cert>" in content
        assert "BEGIN CERTIFICATE" in content
        assert "<key>" in content
        assert "BEGIN ENCRYPTED PRIVATE KEY" in content


# --- main() tests ---


class TestMain:
    def test_happy_path(self, tmp_path: Path) -> None:
        password = "testpass"
        p12_path = tmp_path / "user.p12"
        create_test_p12(p12_path, password.encode("utf-8"))

        template_path = tmp_path / "config.ovpn"
        template_path.write_text("client\n", encoding="utf-8")

        root_key_path = tmp_path / "root.key"
        root_key_path.write_text("ROOT_CA\n", encoding="utf-8")

        src_dir = tmp_path / "src"
        src_dir.mkdir(exist_ok=True)

        import src.ovpn_builder as mod

        original_file = mod.__file__
        inputs = iter(["config", "user"])
        try:
            mod.__file__ = str(src_dir / "ovpn_builder.py")
            with (
                patch("src.ovpn_builder.input", side_effect=lambda _: next(inputs)),
                patch("src.ovpn_builder.getpass.getpass", return_value=password),
            ):
                result = main()
        finally:
            mod.__file__ = original_file

        assert result == 0
        output = tmp_path / "user_neu.ovpn"
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "<ca>" in content
        assert "ROOT_CA" in content

    def test_missing_template(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir(exist_ok=True)

        inputs = iter(["nonexistent", "user"])
        with (
            patch("src.ovpn_builder.__file__", str(src_dir / "ovpn_builder.py")),
            patch("src.ovpn_builder.input", side_effect=lambda _: next(inputs)),
            patch("src.ovpn_builder.getpass.getpass", return_value="pass"),
        ):
            result = main()

        assert result == 1
        assert "nicht gefunden" in capsys.readouterr().err

    def test_missing_p12(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir(exist_ok=True)

        template = tmp_path / "config.ovpn"
        template.write_text("client\n", encoding="utf-8")

        inputs = iter(["config", "nonexistent"])
        with (
            patch("src.ovpn_builder.__file__", str(src_dir / "ovpn_builder.py")),
            patch("src.ovpn_builder.input", side_effect=lambda _: next(inputs)),
            patch("src.ovpn_builder.getpass.getpass", return_value="pass"),
        ):
            result = main()

        assert result == 1
        assert "nicht gefunden" in capsys.readouterr().err

    def test_missing_root_key(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        password = "testpass"
        src_dir = tmp_path / "src"
        src_dir.mkdir(exist_ok=True)

        template = tmp_path / "config.ovpn"
        template.write_text("client\n", encoding="utf-8")
        p12_path = tmp_path / "user.p12"
        create_test_p12(p12_path, password.encode("utf-8"))

        inputs = iter(["config", "user"])
        with (
            patch("src.ovpn_builder.__file__", str(src_dir / "ovpn_builder.py")),
            patch("src.ovpn_builder.input", side_effect=lambda _: next(inputs)),
            patch("src.ovpn_builder.getpass.getpass", return_value=password),
        ):
            result = main()

        assert result == 1
        assert "Root-Key nicht gefunden" in capsys.readouterr().err

    def test_path_traversal_rejected(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir(exist_ok=True)

        inputs = iter(["../../etc/passwd", "user"])
        with (
            patch("src.ovpn_builder.__file__", str(src_dir / "ovpn_builder.py")),
            patch("src.ovpn_builder.input", side_effect=lambda _: next(inputs)),
            patch("src.ovpn_builder.getpass.getpass", return_value="pass"),
        ):
            result = main()

        assert result == 1
        assert "Fehler" in capsys.readouterr().err
