from runtime.security.clock import BAD_OFFSET_MS, UNCERTAIN_OFFSET_MS, ClockProbe, evaluate_clock_health


def test_clock_good_when_offset_below_threshold():
    quality = evaluate_clock_health(ClockProbe(offset_ms=50.0, source="chronyc"))
    assert quality.status == "GOOD"


def test_clock_uncertain_between_thresholds():
    quality = evaluate_clock_health(ClockProbe(offset_ms=(UNCERTAIN_OFFSET_MS + BAD_OFFSET_MS) / 2, source="chronyc"))
    assert quality.status == "UNCERTAIN"


def test_clock_bad_above_threshold():
    quality = evaluate_clock_health(ClockProbe(offset_ms=BAD_OFFSET_MS + 1, source="chronyc"))
    assert quality.status == "BAD"


def test_clock_uncertain_when_probe_has_no_offset():
    quality = evaluate_clock_health(ClockProbe(offset_ms=None, source="unavailable"))
    assert quality.status == "UNCERTAIN"
    assert quality.offset_ms is None


def test_clock_never_reports_good_without_verifiable_offset():
    # This is EDGE-FR-026's core guarantee: an unknown clock state is never presented as synchronized.
    quality = evaluate_clock_health(ClockProbe(offset_ms=None, source="timedatectl"))
    assert quality.status != "GOOD"