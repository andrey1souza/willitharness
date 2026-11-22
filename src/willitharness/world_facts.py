from pathlib import Path

from willitharness.lifecycle import lifecycle_dir, read_resume
from willitharness.paths import inside
from willitharness.plan import Plan
from willitharness.store import UNKNOWN_WORLD
from willitharness.warning_rules import WorldFacts
from willitharness.world import stored_hash


def world_facts(root, plan):
    assert isinstance(root, Path), f"world_facts needs a Path root, got {root!r}. Fix: pass the project directory."
    assert isinstance(plan, Plan), f"world_facts needs a Plan, got {plan!r}. Fix: load the plan."
    world_dir = inside(root, plan.world)
    validated = stored_hash(root, world_dir) if world_dir.is_dir() else None
    resume = read_resume(lifecycle_dir(root, plan))
    facts = WorldFacts(validated, resume is not None and resume.ended_in_changed_world)
    assert facts.validated_hash is None or facts.validated_hash != UNKNOWN_WORLD, f"world_facts returned {facts}. Rule: a stored hash is never the unknown world."
    return facts
