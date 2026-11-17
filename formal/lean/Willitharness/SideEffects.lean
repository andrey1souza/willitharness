import Willitharness.Decision

namespace Willitharness

structure SideEffectReport where
  commandCounts : List (String × Nat × Nat)

def decisionWithReport (_report : SideEffectReport) (r : Reach) (e : EffectResult)
    (g : GuardResult) : Decision :=
  decideRule r e g

theorem S2_side_effects_never_change_decision (s1 s2 : SideEffectReport) (r : Reach)
    (e : EffectResult) (g : GuardResult) :
    decisionWithReport s1 r e g = decisionWithReport s2 r e g := rfl

end Willitharness
