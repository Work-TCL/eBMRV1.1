"""Reference frame format for the generic serial/TCP proprietary adapter -- Document 44 (SPEC-EDGE-002)
DRV-FR-013 ("Custom proprietary protocol lives in isolated adapter with framing/checksum/test vectors").

Document 44 does not name a specific proprietary wire format (unlike Modbus/OPC UA/MQTT, which get their
own reference config sections) -- DRV-FR-013 only requires that *an* isolated adapter exist with real
framing, a real checksum and real test vectors. Rather than inventing an arbitrary scheme, this reference
adapter reuses the checksum convention of NMEA 0183 (the long-established, publicly documented ASCII
serial-sentence protocol used across marine/GPS/industrial instruments): a sentence delimited by `$` and
`*`, with an 8-bit XOR checksum over every byte in between, rendered as two uppercase hex digits. This
adapter adds one field NMEA 0183 does not have -- an explicit 4-hex-digit sequence number -- because
DRV-FR-013's sibling mandatory test (Document 44 section 12: "duplicate/replayed source event where
detectable") requires *something* in the frame a driver can use to recognize a replay; NMEA 0183 itself
has no such field.

Frame:  `$<seq:4 hex><payload>*<checksum:2 hex>\r\n`
Checksum: XOR of every byte of `<seq><payload>` (i.e. everything between `$` and `*`), as two uppercase
hex digits -- identical algorithm to NMEA 0183's own checksum, just over a different body.
"""

from __future__ import annotations

from dataclasses import dataclass

from plugins.common.driver_contracts import CrcError, ProtocolException

_STX = b"$"
_ETX = b"*"


def _xor_checksum(body: bytes) -> int:
    checksum = 0
    for byte in body:
        checksum ^= byte
    return checksum


@dataclass(frozen=True)
class DecodedFrame:
    sequence: int
    payload: bytes


def encode_frame(sequence: int, payload: bytes) -> bytes:
    if not (0 <= sequence <= 0xFFFF):
        raise ValueError("sequence must fit in 16 bits (4 hex digits)")
    body = f"{sequence:04X}".encode("ascii") + payload
    checksum = _xor_checksum(body)
    return _STX + body + _ETX + f"{checksum:02X}".encode("ascii")


def decode_frame(line: bytes) -> DecodedFrame:
    """Raises `ProtocolException` for a structurally malformed line and `CrcError` for a
    structurally valid line whose checksum does not match -- DRV-FR-009's sibling principle for this
    protocol family: a corrupted frame is never silently accepted as if it were good data."""

    if not line.startswith(_STX):
        raise ProtocolException(f"frame missing '$' start delimiter: {line!r}")
    if _ETX not in line:
        raise ProtocolException(f"frame missing '*' checksum delimiter: {line!r}")

    body_and_rest = line[1:]
    etx_index = body_and_rest.index(_ETX)
    body = body_and_rest[:etx_index]
    checksum_hex = body_and_rest[etx_index + 1 :]

    if len(body) < 4:
        raise ProtocolException(f"frame body too short to contain a 4-hex-digit sequence: {line!r}")
    if len(checksum_hex) != 2:
        raise ProtocolException(f"frame checksum field must be exactly 2 hex digits, got {checksum_hex!r}")

    try:
        expected_checksum = int(checksum_hex, 16)
    except ValueError as exc:
        raise ProtocolException(f"frame checksum is not valid hex: {checksum_hex!r}") from exc

    actual_checksum = _xor_checksum(body)
    if actual_checksum != expected_checksum:
        raise CrcError(
            f"frame checksum mismatch: expected {expected_checksum:02X}, computed {actual_checksum:02X}",
            raw_detail=line.decode("ascii", errors="replace"),
        )

    try:
        sequence = int(body[:4], 16)
    except ValueError as exc:
        raise ProtocolException(f"frame sequence field is not valid hex: {body[:4]!r}") from exc

    return DecodedFrame(sequence=sequence, payload=bytes(body[4:]))
