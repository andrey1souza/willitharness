import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_FILE = REPO_ROOT / "zanity-baseline.json"
INHERITED_FINDINGS_CEILING = 30


def baseline_findings():
    return json.loads(BASELINE_FILE.read_text())["findings"]


def test_the_zanity_baseline_never_grows():
    count = len(baseline_findings())
    assert count <= INHERITED_FINDINGS_CEILING, (
        "the baseline holds %d findings, above the ceiling of %d. New findings must be fixed, not added "
        "to the baseline" % (count, INHERITED_FINDINGS_CEILING)
    )


def test_the_baseline_file_has_findings_to_count():
    findings = baseline_findings()
    assert isinstance(findings, list), (
        f"findings must be a list, got {type(findings).__name__}. Rule: the ceiling counts entries. "
        "Fix: regenerate the baseline with zanity or restore the file"
    )
    assert findings, f"the baseline holds {findings!r}; an empty one makes the ceiling check pass for any code, so remove the ceiling instead"
