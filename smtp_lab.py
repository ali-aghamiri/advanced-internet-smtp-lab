"""A minimal SMTP conversation over a raw TCP socket for local study."""

from __future__ import annotations

import re
import socket


class SMTPError(RuntimeError):
    """Raised when a server reply is malformed or rejects a command."""


def _ascii_line(value: str, label: str) -> bytes:
    if not value or any(c in value for c in "\r\n\x00"):
        raise ValueError(f"{label} must be a nonempty single line")
    try:
        return value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{label} must be ASCII for this introductory lab") from exc


def _address(value: str, label: str) -> bytes:
    encoded = _ascii_line(value, label)
    if value.count("@") != 1 or any(c in value for c in " <>\t"):
        raise ValueError(f"{label} must be a simple mailbox address")
    return encoded


def _body_lines(body: str) -> list[bytes]:
    try:
        normalized = body.replace("\r\n", "\n").replace("\r", "\n")
        return [line.encode("ascii") for line in normalized.split("\n")]
    except UnicodeEncodeError as exc:
        raise ValueError("body must be ASCII for this introductory lab") from exc


def send_plain_message(
    host: str,
    port: int,
    sender: str,
    recipient: str,
    subject: str,
    body: str,
    *,
    timeout: float = 5.0,
) -> list[str]:
    """Send one plain ASCII message; return the server's reply transcript.

    This deliberately omits authentication, TLS, SMTPUTF8, attachments, and
    retries. Tests exercise it only against a loopback fake server.
    """

    sender_bytes = _address(sender, "sender")
    recipient_bytes = _address(recipient, "recipient")
    subject_bytes = _ascii_line(subject, "subject")
    lines = _body_lines(body)
    transcript: list[str] = []

    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        with sock.makefile("rb") as incoming:

            def reply(expected: int) -> None:
                for _ in range(20):
                    raw = incoming.readline(8193)
                    if len(raw) > 8192 or not raw.endswith(b"\r\n"):
                        raise SMTPError("malformed or missing SMTP reply")
                    match = re.fullmatch(rb"([0-9]{3})([ -])(.*)\r\n", raw)
                    if not match:
                        raise SMTPError("malformed SMTP reply")
                    code = int(match.group(1))
                    if code != expected:
                        raise SMTPError(f"SMTP {code}: {match.group(3).decode('ascii', 'replace')}")
                    transcript.append(raw.decode("ascii", "replace").rstrip("\r\n"))
                    if match.group(2) == b" ":
                        return
                raise SMTPError("too many reply lines")

            def command(data: bytes, expected: int) -> None:
                sock.sendall(data + b"\r\n")
                reply(expected)

            reply(220)
            command(b"EHLO localhost", 250)
            command(b"MAIL FROM:<" + sender_bytes + b">", 250)
            command(b"RCPT TO:<" + recipient_bytes + b">", 250)
            command(b"DATA", 354)
            headers = (
                b"From: " + sender_bytes + b"\r\n"
                b"To: " + recipient_bytes + b"\r\n"
                b"Subject: " + subject_bytes + b"\r\n\r\n"
            )
            sock.sendall(headers)
            for line in lines:
                sock.sendall((b"." if line.startswith(b".") else b"") + line + b"\r\n")
            sock.sendall(b".\r\n")
            reply(250)
            command(b"QUIT", 221)
    return transcript
