#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CASE_DIRECTORY="$ROOT/fixtures/three-arm-pkill"
SCRIPT_PATH="scripts/gates/three_arm_live.sh"
PLAN_FILE="plan.json"
WORLD_DIRECTORY="world"
TASKS_FILE="tasks.txt"
PROBE_CODE_FILE="$CASE_DIRECTORY/probe/AGENTS.md"
PROBE_DECOY_FILE="$CASE_DIRECTORY/probe-decoy.txt"
PROBE_RUNS=3
PROBE_RUN_CAP_USD="0.01"
FAKE_PROBE_SEED=3
DEFAULT_MODEL="haiku"
ARTIFACTS_ROOT="${WILLITHARNESS_PILOT_ARTIFACTS:-$HOME/.cache/willitharness/pilot}"
EXIT_USAGE=2

mode="print"
reps=""
cap_usd=""
model="$DEFAULT_MODEL"
artifacts_name=""

refuse() {
  echo "$1" >&2
  exit "$EXIT_USAGE"
}

plan_facts() {
  python3 - "$CASE_DIRECTORY/plan/$PLAN_FILE" "$CASE_DIRECTORY/plan/$WORLD_DIRECTORY/$TASKS_FILE" <<'PYTHON'
import json
import sys

DEFAULT_PLAN_REPS = 20
plan = json.load(open(sys.argv[1]))
tasks = [line for line in open(sys.argv[2]).read().splitlines() if line.strip()]
labels = " ".join(arm["label"] for arm in plan["arms"])
print(len(plan["arms"]), plan.get("reps", DEFAULT_PLAN_REPS), len(tasks), plan["run_cap_usd"], labels)
PYTHON
}

cost_of() {
  python3 - "$@" <<'PYTHON'
import sys
from decimal import Decimal

arms, reps, tasks, run_cap, probe_runs, probe_cap = sys.argv[1:7]
runs = Decimal(arms) * Decimal(reps) * Decimal(tasks) * Decimal(run_cap)
probes = Decimal(arms) * Decimal(probe_runs) * Decimal(probe_cap)
print(f"{runs:.2f} {probes:.2f} {runs + probes:.2f}")
PYTHON
}

write_plan_copy() {
  python3 - "$1" "$2" "$3" <<'PYTHON'
import json
import sys
from decimal import Decimal
from pathlib import Path

path, reps, cap = Path(sys.argv[1]), int(sys.argv[2]), Decimal(sys.argv[3])
plan = json.loads(path.read_text())
plan["reps"] = reps
plan["budget_usd"] = float(Decimal(len(plan["arms"])) * reps * cap)
path.write_text(json.dumps(plan, indent=2) + "\n")
for arm in plan["arms"]:
    (path.parent / arm["overlay"]).mkdir(parents=True, exist_ok=True)
PYTHON
}

skill_can_fire() {
  uv run --project "$ROOT" --quiet python - <<'PYTHON'
import sys

from willitharness.claude_agent import build_command, tool_policy

command = build_command("probe", "haiku", 0.01, tool_policy(False, ["ls"]))
tools = command[command.index("--tools") + 1].split(",")
sys.exit(0 if "Skill" in tools and "--disable-slash-commands" not in command else 1)
PYTHON
}

willitharness() {
  uv run --project "$ROOT" --quiet willitharness "$@"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry) mode="dry"; shift ;;
    --live) mode="live"; shift ;;
    --reps) reps="${2:-}"; shift 2 || refuse "--reps needs a value. Rule: a run count is a whole number. Fix: pass --reps N." ;;
    --cap-usd) cap_usd="${2:-}"; shift 2 || refuse "--cap-usd needs a value. Rule: the owner sets the cost cap. Fix: pass --cap-usd with the dollar amount." ;;
    --model) model="${2:-}"; shift 2 || refuse "--model needs a value. Rule: every run records its model. Fix: pass --model with a model name." ;;
    --artifacts) artifacts_name="${2:-}"; shift 2 || refuse "--artifacts needs a value. Rule: a paid run keeps its transcripts. Fix: pass --artifacts NAME." ;;
    *) refuse "unknown option $1. Rule: this script takes --dry, --live, --reps, --cap-usd, --model and --artifacts. Fix: remove $1." ;;
  esac
done

probe_code="$(sed 's/^Verification code: //' "$PROBE_CODE_FILE")"
probe_decoy="$(cat "$PROBE_DECOY_FILE")"
read -r arm_count plan_reps task_count run_cap labels <<<"$(plan_facts)"
reps="${reps:-$plan_reps}"
case "$reps" in
  '' | *[!0-9]* | 0) refuse "run count $reps is not a whole number above 0. Rule: a cell has at least 1 run. Fix: pass --reps with a whole number from 1 to $plan_reps." ;;
esac
if [ "$reps" -gt "$plan_reps" ]; then
  refuse "run count $reps is above the $plan_reps runs per arm of the plan. Rule: the plan sets the most runs the owner approved. Fix: pass --reps $plan_reps or less."
fi
read -r runs_usd probes_usd total_usd <<<"$(cost_of "$arm_count" "$reps" "$task_count" "$run_cap" "$PROBE_RUNS" "$PROBE_RUN_CAP_USD")"

print_command() {
  echo "arms: $labels"
  echo "worst-case run cost: $arm_count arms x $reps reps x $task_count tasks x \$$run_cap cap = \$$runs_usd"
  echo "worst-case probe cost: $arm_count arms x $PROBE_RUNS runs x \$$PROBE_RUN_CAP_USD cap = \$$probes_usd"
  echo "worst-case total: \$$total_usd"
  echo "live command: $SCRIPT_PATH --live --reps $reps --cap-usd $total_usd --model $model --artifacts NAME"
}

print_command
if [ "$mode" = "print" ]; then
  exit 0
fi

if [ "$mode" = "live" ]; then
  [ -n "$cap_usd" ] || refuse "no cost cap given. Rule: the owner sets the cost cap before the run. Fix: pass --cap-usd with at least $total_usd."
  python3 -c 'import sys; sys.exit(0 if float(sys.argv[1]) >= float(sys.argv[2]) else 1)' "$cap_usd" "$total_usd" \
    || refuse "cap \$$cap_usd is below the worst-case total \$$total_usd. Rule: the cap covers the worst case. Fix: pass --cap-usd $total_usd or more, or lower --reps."
  [ -n "$artifacts_name" ] || refuse "no artifacts name given. Rule: a paid run keeps its transcripts. Fix: pass --artifacts NAME."
  case "$artifacts_name" in
    */* | . | ..) refuse "artifacts name $artifacts_name is not one plain folder name. Rule: kept runs live in one folder under $ARTIFACTS_ROOT. Fix: pass a name without slashes." ;;
  esac
  [ ! -e "$ARTIFACTS_ROOT/$artifacts_name" ] || refuse "$ARTIFACTS_ROOT/$artifacts_name exists. Rule: a kept run is never overwritten. Fix: pass a new --artifacts name."
  skill_can_fire || refuse "the run command of this tool cannot reach the skill of arm C. Rule: arm C fires only if the run keeps the Skill tool and does not pass --disable-slash-commands, and a run that cannot fire it measures nothing. Fix: change claude_agent.build_command for plans with a skill arm, then run this script again."
  agent="claude"
else
  agent="fake"
fi

work="$(mktemp -d "${TMPDIR:-/tmp}/willitharness-three-arm-XXXXXX")"
trap 'rm -rf "$work"' EXIT
cp -R "$CASE_DIRECTORY/plan" "$work/plan"
cp -R "$CASE_DIRECTORY/probe" "$work/probe"
write_plan_copy "$work/plan/$PLAN_FILE" "$reps" "$run_cap"
cd "$work/plan"

willitharness plan check "$PLAN_FILE"
willitharness world check "$WORLD_DIRECTORY"
for arm in $labels; do
  if [ "$agent" = "fake" ]; then
    willitharness probe --agent fake --directory "$work/probe" --boundary "$work/probe" --seed "$FAKE_PROBE_SEED" --runs "$PROBE_RUNS" \
      --target-token "$probe_code" --control-token "$probe_decoy" --plan "$PLAN_FILE" --arm "$arm"
  else
    willitharness probe --agent claude --directory "$work/probe" --runs "$PROBE_RUNS" --model "$model" --run-budget-usd "$PROBE_RUN_CAP_USD" \
      --target-token "$probe_code" --control-token "$probe_decoy" --plan "$PLAN_FILE" --arm "$arm"
  fi
done
if [ "$agent" = "fake" ]; then
  willitharness run "$PLAN_FILE" --agent fake
else
  willitharness run "$PLAN_FILE" --agent claude --model "$model"
fi
willitharness analyze "$PLAN_FILE"
willitharness decide "$PLAN_FILE"
willitharness report "$PLAN_FILE"

if [ "$agent" = "claude" ]; then
  mkdir -p "$ARTIFACTS_ROOT/$artifacts_name"
  cp -R .willitharness "$ARTIFACTS_ROOT/$artifacts_name/.willitharness"
  cp "$PLAN_FILE" "$ARTIFACTS_ROOT/$artifacts_name/$PLAN_FILE"
  echo "artifacts: $ARTIFACTS_ROOT/$artifacts_name"
fi
