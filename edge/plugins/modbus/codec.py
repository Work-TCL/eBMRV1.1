"""Modbus register <-> engineering-value codec -- Document 44 section 6's mapping contract:

```yaml
register:
  function: HOLDING
  address: 40010
  length: 2
  data_type: FLOAT32
  byte_order: ABCD
scale: 1.0
```

"Each mapping has test vectors with raw registers -> expected engineering value" (section 6) --
`tests/test_plugin_modbus_tcp.py::test_decode_registers_matches_test_vectors` is that table.

`byte_order` follows the common Modbus 4-letter convention for a 32-bit value split across two
16-bit registers: A/B are the high/low byte of the first-transmitted register, C/D of the second.
ABCD is standard big-endian; DCBA is full little-endian; CDAB/BADC are the two "middle-endian" word/
byte-swap variants every Modbus integration eventually meets in the field.
"""

from __future__ import annotations

import struct

from plugins.common.driver_contracts import PayloadSchemaInvalid

_DATA_TYPE_REGISTER_COUNT = {
    "INT16": 1, "UINT16": 1, "INT32": 2, "UINT32": 2, "FLOAT32": 2,
    "INT64": 4, "UINT64": 4, "FLOAT64": 4,
}

_BYTE_ORDERS = {"ABCD", "BADC", "CDAB", "DCBA"}


def _registers_to_be_bytes(registers: list[int], byte_order: str) -> bytes:
    """Only meaningful for exactly two 16-bit registers (32-bit types) -- the byte_order convention
    Document 44 section 6 shows is defined at that granularity."""

    if len(registers) != 2:
        raise PayloadSchemaInvalid(f"byte_order reordering requires exactly 2 registers, got {len(registers)}")
    a, b = registers[0].to_bytes(2, "big")
    c, d = registers[1].to_bytes(2, "big")
    order = {
        "ABCD": bytes([a, b, c, d]),
        "BADC": bytes([b, a, d, c]),
        "CDAB": bytes([c, d, a, b]),
        "DCBA": bytes([d, c, b, a]),
    }
    if byte_order not in order:
        raise PayloadSchemaInvalid(f"unsupported byte_order: {byte_order!r} (expected one of {_BYTE_ORDERS})")
    return order[byte_order]


def decode_registers(registers: list[int], data_type: str, byte_order: str = "ABCD", scale: float = 1.0) -> float | int:
    """Raises `PayloadSchemaInvalid` for a malformed/unsupported mapping rather than guessing a
    decode -- DRV-FR-009's "never substitute" principle applies to decode ambiguity too."""

    if data_type not in _DATA_TYPE_REGISTER_COUNT:
        raise PayloadSchemaInvalid(f"unsupported data_type: {data_type!r}")
    expected = _DATA_TYPE_REGISTER_COUNT[data_type]
    if len(registers) != expected:
        raise PayloadSchemaInvalid(f"data_type {data_type} requires {expected} register(s), got {len(registers)}")

    if data_type in ("INT16", "UINT16"):
        raw = registers[0]
        value: float | int = raw if data_type == "UINT16" else struct.unpack(">h", raw.to_bytes(2, "big"))[0]
    elif data_type in ("INT32", "UINT32", "FLOAT32"):
        raw_bytes = _registers_to_be_bytes(registers, byte_order)
        fmt = {"INT32": ">i", "UINT32": ">I", "FLOAT32": ">f"}[data_type]
        value = struct.unpack(fmt, raw_bytes)[0]
    else:  # 64-bit types: standard big-endian register order, no byte_order reordering supported yet
        raw_bytes = b"".join(r.to_bytes(2, "big") for r in registers)
        fmt = {"INT64": ">q", "UINT64": ">Q", "FLOAT64": ">d"}[data_type]
        value = struct.unpack(fmt, raw_bytes)[0]

    if scale != 1.0:
        value = value * scale
    return value


def encode_value_to_registers(value: float | int, data_type: str, byte_order: str = "ABCD") -> list[int]:
    """The write-path inverse of `decode_registers` -- used only by `testMapping()`'s preview and unit
    tests. Never called from a poll/read path, and `EdgeDriver.write()` is disabled by default
    (DRV-FR-017), so this function alone cannot reach a live device."""

    if data_type not in _DATA_TYPE_REGISTER_COUNT:
        raise PayloadSchemaInvalid(f"unsupported data_type: {data_type!r}")

    if data_type == "UINT16":
        return [int(value) & 0xFFFF]
    if data_type == "INT16":
        return [struct.unpack(">H", struct.pack(">h", int(value)))[0]]

    if data_type in ("INT32", "UINT32", "FLOAT32"):
        fmt = {"INT32": ">i", "UINT32": ">I", "FLOAT32": ">f"}[data_type]
        raw = struct.pack(fmt, value if data_type == "FLOAT32" else int(value))
        a, b, c, d = raw
        reg0, reg1 = {
            "ABCD": ((a << 8) | b, (c << 8) | d),
            "BADC": ((b << 8) | a, (d << 8) | c),
            "CDAB": ((c << 8) | d, (a << 8) | b),
            "DCBA": ((d << 8) | c, (b << 8) | a),
        }[byte_order]
        return [reg0, reg1]

    fmt = {"INT64": ">q", "UINT64": ">Q", "FLOAT64": ">d"}[data_type]
    raw = struct.pack(fmt, value if data_type == "FLOAT64" else int(value))
    return [int.from_bytes(raw[i : i + 2], "big") for i in range(0, 8, 2)]
