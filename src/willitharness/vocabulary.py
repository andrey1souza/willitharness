from enum import StrEnum


class Verdict(StrEnum):
    INCONCLUSIVE_SMALL_N = "InconclusiveSmallN"
    FIRST_HIGHER = "FirstHigher"
    FIRST_LOWER = "FirstLower"
    INCONCLUSIVE = "Inconclusive"


class NoiseStatus(StrEnum):
    NOISE_UNMEASURED = "NoiseUnmeasured"
    NOISE_FLOOR_TOO_HIGH = "NoiseFloorTooHigh"
    NOISE_OK = "NoiseOk"


class EffectResult(StrEnum):
    RULE_LOWERS_VIOLATIONS = "RuleLowersViolations"
    NO_MEASURABLE_EFFECT = "NoMeasurableEffect"
    RULE_RAISES_VIOLATIONS = "RuleRaisesViolations"
    NOT_ENOUGH_RUNS = "NotEnoughRuns"
    INVALID = "Invalid"


class Reach(StrEnum):
    LOADED = "Loaded"
    MASKED = "Masked"
    UNKNOWN = "Unknown"


class Coverage(StrEnum):
    FULL = "Full"
    PARTIAL = "Partial"
    NONE_SEEN = "NoneSeen"


class GuardResult(StrEnum):
    GUARD_MATCHES_RULE = "GuardMatchesRule"
    GUARD_WORSE = "GuardWorse"
    GUARD_UNTESTED = "GuardUntested"


class Decision(StrEnum):
    FIX_LOADING = "FixLoading"
    KEEP = "Keep"
    REPLACE_WITH_GUARD = "ReplaceWithGuard"
    DELETE_CANDIDATE = "DeleteCandidate"
    NEEDS_MORE_RUNS = "NeedsMoreRuns"
    CANNOT_DECIDE = "CannotDecide"
