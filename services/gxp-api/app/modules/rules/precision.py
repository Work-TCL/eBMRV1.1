"""Document 110 (SPEC-GXP-008) §1/§2 — calculation-class precision, rounding and comparison policy.

Pure and table-driven: no I/O, no session, no `evaluate()` recursion of its own. `CLASS_POLICY` is
`§2`'s calculation-class table transcribed verbatim (storage precision, rounding mode, rounding stage,
comparison rule) -- do not tune any value here to make a test pass (§9). §2 was originally headed
"(PROPOSED)" inside an otherwise APPROVED document; SG-145 is RESOLVED 2026-09-10 (project-owner-
directed, "follow the ebmr-edhr docs"): the "(PROPOSED)" heading is treated as an editorial artefact
inside Document 110 v1.0 APPROVED (whose §1/§3-§10 and approval block are approved as a whole), so §2 is
the approved calculation-class baseline as implemented here. A formal customer QMS Part 11 signature
against Document 110 §2 is still captured at PQ (Document 110 §7); that is a records action, not a code
change. Any change to a value in this table remains a controlled Document 110 revision + revalidation
trigger (Document 110 §7, Document 96).

N2 (rounding only at declared stages, never silently mid-chain) is honoured by construction: this module
never rounds an intermediate arithmetic result. It is invoked from exactly two places --
`expression.py`'s comparison operators (the "at comparison" stage) and `commands.py`'s persistence of a
COMPUTED result (the "at presentation" stage) -- both genuine declared stages, never a bare `+`/`-`/`*`.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, InvalidOperation

from app.mutation.errors import NumericOverflowError, PrecisionPolicyUnresolvedError

ROUNDING_MODES = {"half_up": ROUND_HALF_UP, "half_even": ROUND_HALF_EVEN}


@dataclass(frozen=True)
class ClassPolicy:
    calculation_class: str
    rounding_mode: str | None  # "half_up" | "half_even" | None (no rounding at this stage)
    comparison_dp: int | None | str  # int = fixed dp; "reported" = use the rule's reported_decimal_places; None = compare raw (as captured / exact / source resolution)
    requires_reported_dp: bool = False  # CC-5: "source-specified reported dp" -- the rule must supply it
    gxp_decision: bool = True  # CC-9/CC-10 are explicitly non-GxP / advisory-only per §2's closing paragraph


# Document 110 §2, transcribed. Keys are the ten calculation classes exactly as named.
CLASS_POLICY: dict[str, ClassPolicy] = {
    "CC-1": ClassPolicy("CC-1", rounding_mode=None, comparison_dp=None),  # mass/weight capture -- compare at instrument resolution (raw)
    "CC-2": ClassPolicy("CC-2", rounding_mode=None, comparison_dp=None),  # volume capture -- as captured (raw)
    "CC-3": ClassPolicy("CC-3", rounding_mode="half_up", comparison_dp=6),  # tolerance evaluation
    "CC-4": ClassPolicy("CC-4", rounding_mode="half_up", comparison_dp=6),  # yield/reconciliation -- limit inclusive unless stated (AST operator carries that)
    "CC-5": ClassPolicy("CC-5", rounding_mode="half_up", comparison_dp="reported", requires_reported_dp=True),  # concentration/potency
    "CC-6": ClassPolicy("CC-6", rounding_mode=None, comparison_dp=None),  # count/units -- exact equality, integer values compared raw
    "CC-7": ClassPolicy("CC-7", rounding_mode=None, comparison_dp=None),  # time/duration -- inclusive of declared boundary, raw seconds
    "CC-8": ClassPolicy("CC-8", rounding_mode=None, comparison_dp=None),  # environmental -- per method/limit definition, source resolution
    "CC-9": ClassPolicy("CC-9", rounding_mode="half_even", comparison_dp=None, gxp_decision=False),  # statistical/trending -- advisory only, never a release decision by itself
    "CC-10": ClassPolicy("CC-10", rounding_mode=None, comparison_dp=None, gxp_decision=False),  # financial/commercial -- not a GxP decision path
}

# CC-4 reports at 2dp, CC-9 reports at 4dp (§2, fixed by class); CC-5's is rule-declared (reported_decimal_places).
_FIXED_REPORTED_DP = {"CC-4": 2, "CC-9": 4}


def resolve_class_policy(precision_policy: dict) -> ClassPolicy:
    """Resolves the calculation class a rule's `precision_policy` declares. Raises
    PrecisionPolicyUnresolvedError for an unknown/missing class, or a CC-5 rule missing its required
    `reported_decimal_places` -- fail closed rather than assume a default numeric policy (AG-15)."""
    calc_class = (precision_policy or {}).get("calculation_class")
    if calc_class not in CLASS_POLICY:
        raise PrecisionPolicyUnresolvedError(
            "precision_policy.calculation_class does not resolve to a Document 110 §2 calculation class",
            calculation_class=calc_class,
        )
    policy = CLASS_POLICY[calc_class]
    if policy.requires_reported_dp:
        reported_dp = precision_policy.get("reported_decimal_places")
        if not isinstance(reported_dp, int) or isinstance(reported_dp, bool) or reported_dp < 0:
            raise PrecisionPolicyUnresolvedError(
                f"{calc_class} requires precision_policy.reported_decimal_places (source-specified per §2)",
                calculation_class=calc_class,
            )
    return policy


def reported_decimal_places(policy: ClassPolicy, precision_policy: dict) -> int:
    if policy.calculation_class in _FIXED_REPORTED_DP:
        return _FIXED_REPORTED_DP[policy.calculation_class]
    if policy.requires_reported_dp:
        return precision_policy["reported_decimal_places"]
    raise PrecisionPolicyUnresolvedError(
        f"{policy.calculation_class} has no reported precision to apply", calculation_class=policy.calculation_class
    )


def _comparison_dp(policy: ClassPolicy, precision_policy: dict) -> int | None:
    if policy.comparison_dp == "reported":
        return reported_decimal_places(policy, precision_policy)
    return policy.comparison_dp


def round_at_stage(value: Decimal, policy: ClassPolicy, dp: int) -> tuple[Decimal, Decimal]:
    """Rounds `value` to `dp` decimal places using the class's declared rounding mode. Returns
    (rounded, raw) so the caller can retain the raw value alongside the rounded one (N3/CALC-FR-002).
    Raises NumericOverflowError if the value cannot be represented at this precision (Decimal
    InvalidOperation from a magnitude the default context cannot quantize)."""
    if policy.rounding_mode is None:
        return value, value
    mode = ROUNDING_MODES[policy.rounding_mode]
    quantum = Decimal(1).scaleb(-dp)
    try:
        rounded = value.quantize(quantum, rounding=mode)
    except InvalidOperation as exc:
        raise NumericOverflowError(
            f"Value cannot be represented at {dp} decimal place(s) under {policy.calculation_class}'s "
            "storage precision",
            calculation_class=policy.calculation_class,
        ) from exc
    return rounded, value


DOCUMENT_110_VERSION = "DOCUMENT-110-v1.0"

_PRESENTATION_CLASSES = {"CC-4", "CC-5", "CC-9"}


def presentation_dp(policy: ClassPolicy, precision_policy: dict) -> int | None:
    """The classes whose §2 row declares a presentation/reported stage for a COMPUTED (non-boolean)
    result: CC-4 (checkpoint + presentation, fixed 2dp), CC-5 (reported, rule-declared dp), CC-9 (report
    generation, fixed 4dp). Every other class declares no presentation stage, so its result is never
    rounded a second time after the comparison stage (N2)."""
    if policy.calculation_class not in _PRESENTATION_CLASSES:
        return None
    return reported_decimal_places(policy, precision_policy)


def compare(a: Decimal, b: Decimal, policy: ClassPolicy, precision_policy: dict, op) -> bool:
    """N4: rounds both operands to the class's declared comparison precision (using its rounding mode)
    before applying `op`. A class with no declared comparison precision (raw/as-captured/exact classes)
    compares the unrounded values. The AST's own operator choice (gte vs gt, lte vs lt) is what encodes
    inclusive vs exclusive -- Document 110 does not need a separate inclusivity flag once comparison
    precision is fixed (a value exactly at the rounded boundary and one just outside are no longer
    ambiguous)."""
    dp = _comparison_dp(policy, precision_policy)
    if dp is None:
        return op(a, b)
    a_rounded, _ = round_at_stage(a, policy, dp)
    b_rounded, _ = round_at_stage(b, policy, dp)
    return op(a_rounded, b_rounded)
