import uuid

from runtime.contracts import ClockQuality, RawSourceObservation, SourceRef
from runtime.ingestion.pipeline import MappingRegistry, UnitConversionRule, normalize_observation

GATEWAY_ID = uuid.uuid4()
SITE_ID = uuid.uuid4()


def _raw(**overrides) -> RawSourceObservation:
    defaults = dict(
        connector_id="conn-1", connector_version="1.0", device_id="dev-1", mapping_id="map-1",
        source=SourceRef(protocol="MODBUS_TCP", address="40001"), value=100.0, unit="F",
    )
    defaults.update(overrides)
    return RawSourceObservation(**defaults)


def _clock_good() -> ClockQuality:
    return ClockQuality(status="GOOD", offset_ms=10.0, source="chronyc")


def test_normalize_converts_units_via_registered_rule():
    registry = MappingRegistry()
    registry.register("map-1", [UnitConversionRule(from_unit="F", to_unit="C", factor=0.5555555555555556, offset=-17.77777777777778)])

    envelope = normalize_observation(
        _raw(), gateway_id=GATEWAY_ID, tenant_id="tenant-1", site_id=SITE_ID, gateway_sequence=1,
        clock_quality=_clock_good(), mapping_registry=registry, target_unit="C",
    )

    assert envelope.quality == "GOOD"
    assert envelope.normalized is not None
    assert round(envelope.normalized.value, 2) == 37.78  # 100F -> 37.78C
    assert envelope.raw.value == 100.0  # raw value/unit always retained (EDGE-FR-013)
    assert envelope.raw.unit == "F"
    assert envelope.raw.hash is not None


def test_normalize_degrades_quality_on_uom_incompatible_without_dropping_observation():
    registry = MappingRegistry()  # no rules registered at all

    envelope = normalize_observation(
        _raw(), gateway_id=GATEWAY_ID, tenant_id="tenant-1", site_id=SITE_ID, gateway_sequence=1,
        clock_quality=_clock_good(), mapping_registry=registry, target_unit="C",
    )

    assert envelope.quality == "BAD"
    assert envelope.normalized is None
    assert envelope.raw.value == 100.0  # observation is still delivered, never silently dropped


def test_normalize_marks_clock_uncertain_when_clock_bad():
    registry = MappingRegistry()
    bad_clock = ClockQuality(status="BAD", offset_ms=9999.0, source="chronyc")

    envelope = normalize_observation(
        _raw(quality_hint="GOOD"), gateway_id=GATEWAY_ID, tenant_id="tenant-1", site_id=SITE_ID, gateway_sequence=1,
        clock_quality=bad_clock, mapping_registry=registry,
    )

    assert envelope.quality == "CLOCK_UNCERTAIN"


def test_normalize_preserves_source_provenance():
    envelope = normalize_observation(
        _raw(), gateway_id=GATEWAY_ID, tenant_id="tenant-1", site_id=SITE_ID, gateway_sequence=42,
        clock_quality=_clock_good(), mapping_registry=MappingRegistry(),
    )

    assert envelope.gateway_id == GATEWAY_ID
    assert envelope.connector_id == "conn-1"
    assert envelope.device_id == "dev-1"
    assert envelope.mapping_id == "map-1"
    assert envelope.gateway_sequence == 42
    assert envelope.source.protocol == "MODBUS_TCP"
    assert envelope.schema_version == "1.0"