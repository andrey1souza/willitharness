from collections import Counter, defaultdict
from dataclasses import dataclass

from willitharness.outcomes import TARGET_OUTCOME
from willitharness.plan import DEFAULT_REPS
from willitharness.store import UNKNOWN_MODEL, UNKNOWN_WORLD, latest_by_run
from willitharness.verdict import MIN_RUNS
from willitharness.vocabulary import Verdict

LOW_N_WARNING = "W-LOWN: arm {arm}, task {task} has {n} usable runs; {recommended} are recommended"
DENIAL_WARNING = "W-DENIAL: arm {arm}, task {task}: every run has a permission denial"
SATURATED_WARNING = "saturated: arm {arm}, task {task} has no violating run; not measurable at this n; the model may already obey the rule"
WORLD_MIX_WARNING = "W-WORLD: arm {arm}, task {task} has runs from {worlds} worlds; the runs do not share one validated world"
LEFT_WORLD_WARNING = "W-WORLD: arm {arm}, task {task} has {n} runs that left the validated world {validated}; their world hash differs from the validated hash"
NO_HASH_WARNING = "W-NOHASH: {n} runs carry no world hash; they were recorded before T62 and cannot show a mixed world"
MODEL_MIX_WARNING = "W-MODEL: the plan has runs on {n} models: {models}; runs on different models are not one result"
NO_MODEL_WARNING = "W-NOMODEL: {n} runs carry no model name; they were recorded before T73 and may use another model"
ENDED_CHANGED_WARNING = "W-WORLD: the plan ended while its world differed from the validated one; run willitharness world check and run the plan again before you trust it"
POOLED_WARNING = "pooled: task clustering is ignored"
AT_BOUND_WARNING = "AtBound: {outcome}, task {task}, arm {first} against arm {second}: both arms at 0% (or 100%); harder tasks are needed"


def at_bound(first, second):
    assert first.runs >= 0 and second.runs >= 0, f"run counts must not be negative: {first.runs}, {second.runs}"
    assert MIN_RUNS >= 1, f"MIN_RUNS must keep both arms measured, got {MIN_RUNS}"
    both_zero = first.successes == 0 and second.successes == 0
    both_full = first.successes == first.runs and second.successes == second.runs
    result = first.runs >= 1 and second.runs >= 1 and (both_zero or both_full)
    assert not result or min(first.runs, second.runs) >= 1, f"AtBound for an empty arm: {first}, {second}"
    return result


def cell_warnings(counts, denied):
    assert all(item.runs >= 0 for item in counts.values()), f"negative run count in {counts}"
    assert denied <= set(counts), f"denied cells {denied} are not all cells of {sorted(counts)}"
    lines = []
    for cell in sorted(counts):
        if counts[cell].runs < DEFAULT_REPS:
            lines.append(LOW_N_WARNING.format(arm=cell.arm, task=cell.task, n=counts[cell].runs, recommended=DEFAULT_REPS))
        if cell in denied:
            lines.append(DENIAL_WARNING.format(arm=cell.arm, task=cell.task))
    assert all(isinstance(line, str) for line in lines), f"cell_warnings must return text, got {lines}"
    return lines


@dataclass(frozen=True)
class WorldFacts:
    validated_hash: str | None
    ended_in_changed_world: bool


NO_WORLD_FACTS = WorldFacts(None, False)


def world_mix_lines(records):
    assert isinstance(records, tuple), f"world_mix_lines needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    worlds = defaultdict(set)
    for run in latest_by_run(records).values():
        if run.world_hash != UNKNOWN_WORLD:
            worlds[(run.arm, run.task)].add(run.world_hash)
    lines = [WORLD_MIX_WARNING.format(arm=arm, task=task, worlds=len(hashes)) for (arm, task), hashes in sorted(worlds.items()) if len(hashes) > 1]
    assert len(lines) <= len(worlds), f"world_mix_lines made {len(lines)} lines for {len(worlds)} cells"
    return lines


def left_world_lines(records, validated):
    assert validated is None or validated != UNKNOWN_WORLD, f"the validated hash {validated!r} is empty. Rule: a stored hash is never the unknown world. Fix: pass the hash world check stored."
    left = defaultdict(int)
    for run in latest_by_run(records).values():
        if validated is not None and run.world_hash not in (UNKNOWN_WORLD, validated):
            left[(run.arm, run.task)] += 1
    lines = [LEFT_WORLD_WARNING.format(arm=arm, task=task, n=count, validated=validated) for (arm, task), count in sorted(left.items())]
    assert len(lines) == len(left), f"left_world_lines made {len(lines)} lines for {len(left)} cells"
    return lines


def no_hash_lines(records):
    assert isinstance(records, tuple), f"no_hash_lines needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    unhashed = sum(1 for run in latest_by_run(records).values() if run.world_hash == UNKNOWN_WORLD)
    lines = [NO_HASH_WARNING.format(n=unhashed)] if unhashed else []
    assert len(lines) <= 1, f"no_hash_lines made {len(lines)} lines. Rule: the count is one line."
    return lines


def world_warnings(records, world):
    assert isinstance(records, tuple), f"world_warnings needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    assert all(hasattr(record, "world_hash") for record in records), f"a record has no world_hash in {records!r}. Rule: T62, every record carries the world hash. Fix: build records with Record."
    assert isinstance(world, WorldFacts), f"world_warnings needs WorldFacts, got {world!r}. Fix: build them with world_facts."
    lines = [*world_mix_lines(records), *left_world_lines(records, world.validated_hash), *no_hash_lines(records)]
    lines += [ENDED_CHANGED_WARNING] if world.ended_in_changed_world else []
    assert all(isinstance(line, str) for line in lines), f"world_warnings must return text, got {lines}"
    return lines


def model_warnings(records):
    assert isinstance(records, tuple), f"model_warnings needs a tuple of records, got {type(records).__name__}. Fix: pass load_records output."
    assert all(hasattr(record, "model") for record in records), f"a record has no model in {records!r}. Rule: T73, every record carries the model name. Fix: build records with Record."
    runs = Counter(run.model for run in latest_by_run(records).values())
    unnamed = runs.pop(UNKNOWN_MODEL, 0)
    lines = []
    if len(runs) > 1:
        lines.append(MODEL_MIX_WARNING.format(n=len(runs), models=", ".join(f"{model} {count} runs" for model, count in sorted(runs.items()))))
    if unnamed:
        lines.append(NO_MODEL_WARNING.format(n=unnamed))
    assert len(lines) <= 2, f"model_warnings made {len(lines)} lines. Rule: one mix line and one count line."
    return lines


def row_warnings(rows):
    lines = []
    for row in rows:
        if row.pooled:
            lines.append(POOLED_WARNING)
        if row.outcome == TARGET_OUTCOME and row.first_counts.runs >= 1 and row.first_counts.successes == 0:
            lines.append(SATURATED_WARNING.format(arm=row.first, task=row.task))
        if row.verdict is Verdict.INCONCLUSIVE and at_bound(row.first_counts, row.second_counts):
            lines.append(AT_BOUND_WARNING.format(outcome=row.outcome, task=row.task, first=row.first, second=row.second))
    unique = list(dict.fromkeys(lines))
    assert len(unique) <= len(lines), f"row_warnings invented lines: {unique} from {lines}"
    assert all(isinstance(line, str) for line in unique), f"row_warnings must return text, got {unique}"
    return unique
