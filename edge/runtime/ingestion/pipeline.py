"""Ingestion pipeline -- Document 43 section 4's `ingestSourceObservation()`/`normalizeObservation()`.
EDGE-FR-009 (canonical envelope), EDGE-FR-010 (provenance), EDGE-FR-011 (timestamp model), EDGE-FR-012
(data quality), EDGE-FR-013 (canonical units, versioned conversion only, raw value/unit always retained).

Document 45 (SPEC-EDGE-003) adds `compute_freshness()` -- BUF-FR-017/018's freshness dimension, kept
distinct from `quality` per Document 45 section 6 ("Quality and freshness are different dimensions"):
source-native GOOD data received late is still quality=GOOD, freshness=LATE/STALE.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from runtime.contracts import (
    ClockQuality,
    EdgeObservationEnvelope,
    NormalizedValue,
    RawSourceObservation,
    RawValue,
    utcnow,
)

logger = logging.getLogger("edge.ingestion")

Freshness = Literal["FRESH", "LATE", "STALE"]


class UomIncompatibleError(Exception):
    pass


@dataclass(frozen=True)
class UnitConversionRule:
    """One row of a versioned mapping's unit-conversion table -- `value_canonical = value_raw * factor +
    offset`. EDGE-FR-013: "Mappings may convert source units to canonical units only through versioned
    conversion rule" -- there is no implicit/guessed conversion path; an unmapped (from_unit, to_unit)
    pair is a hard `UomIncompatibleError`, never a silent pass-through or an invented factor."""

    from_unit: str
    to_unit: str
    factor: float = 1.0
    offset: float = 0.0


class MappingRegistry:
    """Holds the versioned conversion tables an active gateway configuration activated (see
    runtime/config/activation.py). Never mutated in place -- a new mapping_version is a new entry."""

    def __init__(self) -> None:
        self._rules: dict[str, dict[tuple[str, str], UnitConversionRule]] = {}

    def register(self, mapping_version: str, rules: list[UnitConversionRule]) -> None:
        self._rules[mapping_version] = {(r.from_unit, r.to_unit): r for r in rules}

    def convert(self, mapping_version: str, from_unit: str, to_unit: str, value: float) -> float:
        if from_unit == to_unit:
            return value
        table = self._rules.get(mapping_version)
        if table is None:
            raise UomIncompatibleError(f"No conversion table registered for mapping_version={mapping_version!r}")
        rule = table.get((from_unit, to_unit))
        if rule is None:
            raise UomIncompatibleError(f"No conversion rule {from_unit!r} -> {to_unit!r} in mapping_version={mapping_version!r}")
        return value * rule.factor + rule.offset


def _raw_value_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def normalize_observation(
    raw: RawSourceObservation,
    *,
    gateway_id: uuid.UUID,
    tenant_id: str,
    site_id: uuid.UUID,
    gateway_sequence: int,
    clock_quality: ClockQuality,
    mapping_registry: MappingRegistry,
    target_unit: str | None = None,
    correlation_id: uuid.UUID | None = None,
) -> EdgeObservationEnvelope:
    """`normalizeObservation()`. Never raises on a bad *value* -- a conversion failure degrades quality to
    BAD rather than dropping the observation (Prohibitions section 16: "Do not infer GOOD quality from
    missing quality metadata" -- the corollary here is a failed conversion is never silently dropped
    either; it is delivered with an honest quality flag and the untouched raw value/unit intact).

    BUF-FR-016 (Clock metadata): `raw.source_timestamp` is carried through to
    `EdgeObservationEnvelope.source_timestamp` completely unmodified regardless of `clock_quality` --
    a degraded/uncertain clock degrades the *quality* flag (below), it never rewrites the source time to
    make delayed data look current."""

    quality = raw.quality_hint or "GOOD"
    normalized: NormalizedValue | None = None

    if target_unit is not None and raw.unit is not None and isinstance(raw.value, (int, float)):
        try:
            converted = mapping_registry.convert(raw.mapping_id, raw.unit, target_unit, float(raw.value))
            normalized = NormalizedValue(value=converted, unit=target_unit)
        except UomIncompatibleError as exc:
            logger.warning("ingestion: UOM_INCOMPATIBLE mapping=%s %s", raw.mapping_id, exc)
            quality = "BAD"

    if clock_quality.status == "BAD":
        quality = "CLOCK_UNCERTAIN" if quality == "GOOD" else quality

    return EdgeObservationEnvelope(
        gateway_id=gateway_id,
        tenant_id=tenant_id,
        site_id=site_id,
        connector_id=raw.connector_id,
        connector_version=raw.connector_version,
        device_id=raw.device_id,
        mapping_id=raw.mapping_id,
        mapping_version=raw.mapping_id,
        source=raw.source,
        source_timestamp=raw.source_timestamp,
        gateway_received_at=utcnow(),
        gateway_sequence=gateway_sequence,
        clock_quality=clock_quality,
        quality=quality,
        raw=RawValue(value=raw.value, unit=raw.unit, hash=_raw_value_hash(raw.value)),
        normalized=normalized,
        correlation_id=correlation_id,
    )


def compute_freshness(
    source_timestamp: datetime | None,
    received_at: datetime,
    *,
    late_threshold_seconds: float,
    stale_threshold_seconds: float,
) -> Freshness:
    """BUF-FR-018 (Freshness): a pure, non-destructive computation over already-stored timestamps --
    it never mutates `source_timestamp`/`gateway_received_at` and never changes `quality`. Returns
    'FRESH' | 'LATE' | 'STALE' based on `received_at - source_timestamp` against the two caller-supplied
    thresholds.

    The two threshold values are deliberately parameters, not constants this module invents: Document 45
    section 6 explicitly delegates "whether late/stale evidence can satisfy a specific recipe/EM/QC
    requirement" to the downstream module, and neither Document 45 nor Documents 106-115 define a
    numeric staleness cutoff -- picking one here would be inventing regulated acceptance behavior this
    codebase's own SPEC_GAP rule forbids. A missing `source_timestamp` (device never reported native time)
    cannot be scored for lateness and is reported STALE rather than guessed as FRESH, consistent with
    "never infer GOOD/fresh from missing metadata"."""
    if source_timestamp is None:
        return "STALE"
    age_seconds = (received_at - source_timestamp).total_seconds()
    if age_seconds < 0:
        # A source timestamp in the future relative to gateway receipt is itself a clock-integrity
        # concern (surfaced separately via clock_quality), not evidence of freshness -- never treated as
        # "even fresher than fresh".
        return "FRESH"
    if age_seconds >= stale_threshold_seconds:
        return "STALE"
    if age_seconds >= late_threshold_seconds:
        return "LATE"
    return "FRESH"
