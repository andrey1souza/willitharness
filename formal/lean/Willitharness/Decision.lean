namespace Willitharness

inductive Reach where
  | loaded
  | masked
  | unknown
  deriving DecidableEq, Repr

inductive EffectResult where
  | ruleLowersViolations
  | noMeasurableEffect
  | ruleRaisesViolations
  | notEnoughRuns
  | invalid
  deriving DecidableEq, Repr

inductive GuardResult where
  | guardMatchesRule
  | guardWorse
  | guardUntested
  deriving DecidableEq, Repr

inductive Decision where
  | fixLoading
  | keep
  | replaceWithGuard
  | deleteCandidate
  | needsMoreRuns
  | cannotDecide
  deriving DecidableEq, Repr

def Reach.name : Reach → String
  | .loaded => "Loaded"
  | .masked => "Masked"
  | .unknown => "Unknown"

def EffectResult.name : EffectResult → String
  | .ruleLowersViolations => "RuleLowersViolations"
  | .noMeasurableEffect => "NoMeasurableEffect"
  | .ruleRaisesViolations => "RuleRaisesViolations"
  | .notEnoughRuns => "NotEnoughRuns"
  | .invalid => "Invalid"

def GuardResult.name : GuardResult → String
  | .guardMatchesRule => "GuardMatchesRule"
  | .guardWorse => "GuardWorse"
  | .guardUntested => "GuardUntested"

def Decision.name : Decision → String
  | .fixLoading => "FixLoading"
  | .keep => "Keep"
  | .replaceWithGuard => "ReplaceWithGuard"
  | .deleteCandidate => "DeleteCandidate"
  | .needsMoreRuns => "NeedsMoreRuns"
  | .cannotDecide => "CannotDecide"

def decideRule : Reach → EffectResult → GuardResult → Decision
  | .masked, _, _ => .fixLoading
  | .unknown, _, _ => .cannotDecide
  | .loaded, .invalid, _ => .cannotDecide
  | .loaded, .notEnoughRuns, _ => .needsMoreRuns
  | .loaded, .ruleRaisesViolations, _ => .deleteCandidate
  | .loaded, .noMeasurableEffect, _ => .deleteCandidate
  | .loaded, .ruleLowersViolations, .guardMatchesRule => .replaceWithGuard
  | .loaded, .ruleLowersViolations, .guardWorse => .keep
  | .loaded, .ruleLowersViolations, .guardUntested => .keep

theorem D1_masked_fix_loading (e : EffectResult) (g : GuardResult) :
    decideRule .masked e g = .fixLoading := rfl

theorem D2_unknown_cannot_decide (e : EffectResult) (g : GuardResult) :
    decideRule .unknown e g = .cannotDecide := rfl

theorem D3_loaded_invalid_cannot_decide (g : GuardResult) :
    decideRule .loaded .invalid g = .cannotDecide := by
  cases g <;> rfl

theorem D4_loaded_not_enough_runs (g : GuardResult) :
    decideRule .loaded .notEnoughRuns g = .needsMoreRuns := by
  cases g <;> rfl

theorem D5_loaded_raises_delete_candidate (g : GuardResult) :
    decideRule .loaded .ruleRaisesViolations g = .deleteCandidate := by
  cases g <;> rfl

theorem D6_loaded_no_effect_delete_candidate (g : GuardResult) :
    decideRule .loaded .noMeasurableEffect g = .deleteCandidate := by
  cases g <;> rfl

theorem D7_replace_with_guard :
    decideRule .loaded .ruleLowersViolations .guardMatchesRule = .replaceWithGuard := rfl

theorem D8_keep_when_guard_not_matching (g : GuardResult) (h : g ≠ .guardMatchesRule) :
    decideRule .loaded .ruleLowersViolations g = .keep := by
  cases g
  · exact absurd rfl h
  · rfl
  · rfl

theorem D9_total (r : Reach) (e : EffectResult) (g : GuardResult) :
    ∃ d, decideRule r e g = d := ⟨_, rfl⟩

theorem D9_deterministic (r : Reach) (e : EffectResult) (g : GuardResult)
    (d1 d2 : Decision) (h1 : decideRule r e g = d1) (h2 : decideRule r e g = d2) : d1 = d2 := by
  rw [← h1, ← h2]

theorem D10_replace_only_when_justified (r : Reach) (e : EffectResult) (g : GuardResult)
    (h : decideRule r e g = .replaceWithGuard) :
    r = .loaded ∧ e = .ruleLowersViolations ∧ g = .guardMatchesRule := by
  cases r <;> cases e <;> cases g <;> simp_all [decideRule]

theorem D11_no_delete_when_rule_lowers (r : Reach) (g : GuardResult) :
    decideRule r .ruleLowersViolations g ≠ .deleteCandidate := by
  cases r <;> cases g <;> simp [decideRule]

theorem D12_masked_never_keep_replace_delete (e : EffectResult) (g : GuardResult) :
    decideRule .masked e g ≠ .keep ∧ decideRule .masked e g ≠ .replaceWithGuard ∧
      decideRule .masked e g ≠ .deleteCandidate := by
  rw [D1_masked_fix_loading]
  exact ⟨by decide, by decide, by decide⟩

def allReach : List Reach := [.loaded, .masked, .unknown]

def allEffect : List EffectResult :=
  [.ruleLowersViolations, .noMeasurableEffect, .ruleRaisesViolations, .notEnoughRuns, .invalid]

def allGuard : List GuardResult := [.guardMatchesRule, .guardWorse, .guardUntested]

def allInputs : List (Reach × EffectResult × GuardResult) :=
  allReach.flatMap fun r => allEffect.flatMap fun e => allGuard.map fun g => (r, e, g)

theorem allInputs_length : allInputs.length = 45 := by decide

theorem allInputs_complete (r : Reach) (e : EffectResult) (g : GuardResult) :
    (r, e, g) ∈ allInputs := by
  cases r <;> cases e <;> cases g <;> decide

def rowSafe (x : Reach × EffectResult × GuardResult) : Prop :=
  (decideRule x.1 x.2.1 x.2.2 = .replaceWithGuard →
      x.1 = .loaded ∧ x.2.1 = .ruleLowersViolations ∧ x.2.2 = .guardMatchesRule) ∧
  (x.2.1 = .ruleLowersViolations → decideRule x.1 x.2.1 x.2.2 ≠ .deleteCandidate) ∧
  (x.1 = .masked → decideRule x.1 x.2.1 x.2.2 = .fixLoading)

instance (x : Reach × EffectResult × GuardResult) : Decidable (rowSafe x) := by
  unfold rowSafe
  exact inferInstance

theorem exhaustive_D10_D11_D12 : ∀ x ∈ allInputs, rowSafe x := by
  decide

end Willitharness
