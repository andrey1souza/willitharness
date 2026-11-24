from willitharness.plan import Plan


def missing_rule(plan):
    assert isinstance(plan, Plan), f"missing_rule needs a Plan, got {plan!r}. Fix: pass site.plan."
    if plan.rule is not None:
        return None
    message = f"plan {plan.name} has no rule. Rule: L1, a run needs a plan rule, so that every run stores an outcome that analyze can read. Fix: add a rule object with id, file, section, target_outcome and detector to the plan."
    assert "Rule:" in message and "Fix:" in message, f"the missing rule message {message!r} lacks Rule: or Fix:. Rule: a refusal states a rule and a fix."
    return message
