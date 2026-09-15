"""DRV-FR-011 ("JSON/binary/custom payload decoded only through versioned decoder plugin/schema") --
Document 44 section 7's `decoder: filler-v2` / `schema_version: "2.1"` mapping fields name exactly this:
an MQTT payload is never handed to a generic/ad-hoc parser. Every connector config names one decoder id
by its registered identity; an unknown id or a payload that fails that decoder's own schema check both
fail closed with `PayloadSchemaInvalid` (Document 44 section 9's stable error taxonomy) rather than
falling back to "best-effort" parsing.

This reference build registers one decoder, `generic-json-v1`: a UTF-8 JSON object carrying a
`schema_version` field that must match the connector's configured `schema_version` exactly, plus a
required `value` field. Real deployments register their own decoder ids/versions for each instrument's
actual payload shape (Document 44 section 7's `filler-v2` is a customer/site-specific example, not a
built-in one this codebase can honestly claim to ship) -- adding one is a matter of registering another
function in `DECODERS`, never relaxing the "versioned decoder only" rule itself.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from plugins.common.driver_contracts import PayloadSchemaInvalid


class DecodedMqttPayload:
    __slots__ = ("value", "unit", "parameter_code", "source_timestamp_iso")

    def __init__(
        self, *, value: Any, unit: str | None = None, parameter_code: str | None = None,
        source_timestamp_iso: str | None = None,
    ) -> None:
        self.value = value
        self.unit = unit
        self.parameter_code = parameter_code
        self.source_timestamp_iso = source_timestamp_iso


def decode_generic_json_v1(payload: bytes, expected_schema_version: str) -> DecodedMqttPayload:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PayloadSchemaInvalid("MQTT payload is not valid UTF-8", raw_detail=str(exc)) from exc
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PayloadSchemaInvalid("MQTT payload is not valid JSON", raw_detail=str(exc)) from exc
    if not isinstance(obj, dict):
        raise PayloadSchemaInvalid(f"MQTT JSON payload must be an object, got {type(obj).__name__}")

    schema_version = obj.get("schema_version")
    if schema_version != expected_schema_version:
        raise PayloadSchemaInvalid(
            f"MQTT payload schema_version mismatch: connector expects {expected_schema_version!r}, "
            f"payload declared {schema_version!r}"
        )
    if "value" not in obj:
        raise PayloadSchemaInvalid("MQTT payload missing required field: value")

    return DecodedMqttPayload(
        value=obj["value"], unit=obj.get("unit"), parameter_code=obj.get("parameter_code"),
        source_timestamp_iso=obj.get("timestamp"),
    )


DECODERS: dict[str, Callable[[bytes, str], DecodedMqttPayload]] = {
    "generic-json-v1": decode_generic_json_v1,
}


def get_decoder(decoder_id: str) -> Callable[[bytes, str], DecodedMqttPayload]:
    try:
        return DECODERS[decoder_id]
    except KeyError as exc:
        raise PayloadSchemaInvalid(
            f"no released MQTT decoder registered for decoder id {decoder_id!r} -- "
            f"known decoders: {sorted(DECODERS)}"
        ) from exc
