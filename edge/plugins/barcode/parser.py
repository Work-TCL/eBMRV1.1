"""Versioned barcode parser -- Document 46 PER-FR-004 ("Versioned barcode parser supports GS1/UDI/
custom/internal labels; raw scan retained"). Document 46 section 6 is explicit that parsing is a
separate, stateless step from business validation ("Never assume a syntactically valid barcode is
authorized for the current batch") -- this module only turns raw scanned text into structured fields; it
never looks up or judges whether the parsed identity is the *correct* material/lot/serial for the
current operation (that is `validateScanForAction()`, PER-FR-005, a domain/server-side function this
edge plugin does not implement -- see the module docstring in scanner.py).

`PARSER_ID`/`PARSER_VERSION` are carried on every `ScanObservation` so a downstream consumer can always
tell which parser rules produced a given `parsed` structure, even after this module changes -- Document 43
Architectural Principles: "All inbound industrial data uses versioned mapping/configuration."
"""

from __future__ import annotations

from dataclasses import dataclass, field

PARSER_ID = "doc46-gs1-udi-custom"
PARSER_VERSION = "1.0.0"

# GS1 Application Identifiers relevant to DDCP/pharma/device labels (Document 46 section 1's "packaging/
# dispensing/eDHR" scope). UDI carriers on FDA-regulated devices are themselves GS1 element strings using
# these same AIs (per FDA's GS1 UDI guidance), so UDI and GS1 share one table rather than needing a second
# parser -- a barcode carrying AI (01) is both a GS1 GTIN and, in a UDI context, the Device Identifier.
_GS1_AI_FIELD_LENGTHS: dict[str, tuple[str, int | None]] = {
    "00": ("sscc", 18),
    "01": ("gtin", 14),
    "10": ("lot", None),  # variable length, FNC1-terminated
    "11": ("prod_date", 6),
    "17": ("expiry", 6),
    "21": ("serial", None),  # variable length, FNC1-terminated
    "240": ("custom_additional_id", None),
    "8005": ("price_per_unit", 6),
}

_FNC1 = "\x1d"  # GS1 field separator (ASCII 29) terminates variable-length AI fields mid-string


@dataclass(frozen=True)
class ParsedIdentity:
    entity_type: str | None = None
    product_code: str | None = None
    lot: str | None = None
    serial: str | None = None
    udi: str | None = None
    expiry: str | None = None
    custom: dict[str, str] = field(default_factory=dict)


def _parse_gs1_element_string(body: str) -> ParsedIdentity:
    """`body` is the barcode payload after any symbology-specific prefix has already been stripped by
    the caller. Malformed/unknown AIs are preserved under `custom` rather than dropped -- PER-FR-004's
    "raw scan retained" plus this module's own no-silent-loss rule; an AI this table does not recognize is
    not evidence of a wrong scan, only of a label variant this parser version does not model."""
    fields: dict[str, str] = {}
    custom: dict[str, str] = {}
    i = 0
    while i < len(body):
        matched = False
        for ai_len in (4, 3, 2):
            ai = body[i : i + ai_len]
            if ai in _GS1_AI_FIELD_LENGTHS:
                name, fixed_len = _GS1_AI_FIELD_LENGTHS[ai]
                start = i + ai_len
                if fixed_len is not None:
                    value = body[start : start + fixed_len]
                    i = start + fixed_len
                else:
                    end = body.find(_FNC1, start)
                    if end == -1:
                        end = len(body)
                    value = body[start:end]
                    i = end + 1 if end < len(body) else end
                if name in ("gtin", "lot", "serial", "prod_date", "expiry"):
                    fields[name] = value
                else:
                    custom[ai] = value
                matched = True
                break
        if not matched:
            # Unrecognized byte at this position -- stop rather than guess a boundary; whatever was
            # already decoded is still returned (never fabricate a field past this point).
            custom.setdefault("_undecoded_tail", body[i:])
            break

    return ParsedIdentity(
        entity_type="gs1_element_string",
        product_code=fields.get("gtin"),
        lot=fields.get("lot"),
        serial=fields.get("serial"),
        udi=fields.get("gtin") and f"(01){fields['gtin']}" or None,
        expiry=fields.get("expiry"),
        custom=custom,
    )


def _parse_custom_internal(body: str) -> ParsedIdentity:
    """Fallback for site-internal label formats that are not GS1 element strings -- Document 46 PER-FR-004
    names "custom/internal labels" as an explicit format class. This reference build recognizes a simple
    `KEY:VALUE|KEY:VALUE` internal convention; anything else is preserved verbatim under `custom["raw"]`
    rather than rejected, since a barcode plugin's job is acquisition, not authorization (section 6)."""
    if ":" not in body:
        return ParsedIdentity(entity_type="custom_unstructured", custom={"raw": body})
    parts: dict[str, str] = {}
    for segment in body.split("|"):
        if ":" in segment:
            key, _, value = segment.partition(":")
            parts[key.strip().lower()] = value.strip()
    return ParsedIdentity(
        entity_type="custom_internal",
        product_code=parts.get("product") or parts.get("pc"),
        lot=parts.get("lot"),
        serial=parts.get("serial") or parts.get("sn"),
        custom={k: v for k, v in parts.items() if k not in ("product", "pc", "lot", "serial", "sn")},
    )


def parse_scan(raw: str) -> ParsedIdentity:
    """Deterministic: same `raw` input with this `PARSER_VERSION` always yields the same `ParsedIdentity`
    (PER-FR-004's "Deterministic parsing" acceptance intent) -- no clock, randomness or network lookup."""
    if raw.startswith("]") and len(raw) > 3:
        # AIM symbology identifier prefix (e.g. "]C1", "]d2") signals a GS1-encoded barcode per the
        # scanner's own symbology reporting -- strip it before parsing the element string.
        return _parse_gs1_element_string(raw[3:])
    if raw[:2] in _GS1_AI_FIELD_LENGTHS or raw[:3] in _GS1_AI_FIELD_LENGTHS or raw[:4] in _GS1_AI_FIELD_LENGTHS:
        return _parse_gs1_element_string(raw)
    return _parse_custom_internal(raw)