import Willitharness.Verdict
import Willitharness.Decision
import Willitharness.Probe

namespace Willitharness

inductive NoiseStatus where
  | noiseUnmeasured
  | noiseFloorTooHigh
  | noiseOk
  deriving DecidableEq, Repr

def allNoise : List NoiseStatus := [.noiseUnmeasured, .noiseFloorTooHigh, .noiseOk]

def allVerdict : List Verdict :=
  [.inconclusiveSmallN, .firstHigher, .firstLower, .inconclusive]

def noiseStatusOf [DiffOracle] (a a2 : Counts) : NoiseStatus :=
  match verdictOf a a2 with
  | .inconclusiveSmallN => .noiseUnmeasured
  | .firstHigher => .noiseFloorTooHigh
  | .firstLower => .noiseFloorTooHigh
  | .inconclusive => .noiseOk

theorem verdict_not_small [DiffOracle] (a b : Counts) (hs : ¬ min a.n b.n < MinRuns) :
    verdictOf a b ≠ .inconclusiveSmallN := by
  unfold verdictOf
  rw [ite_eq_right hs]
  by_cases p : 0 < (DiffOracle.diff a b).1
  · rw [ite_eq_left p]
    decide
  · rw [ite_eq_right p]
    by_cases q : (DiffOracle.diff a b).2 < 0
    · rw [ite_eq_left q]
      decide
    · rw [ite_eq_right q]
      decide

theorem V6_unmeasured_iff [DiffOracle] (a a2 : Counts) :
    noiseStatusOf a a2 = .noiseUnmeasured ↔ min a.n a2.n < MinRuns := by
  by_cases hs : min a.n a2.n < MinRuns
  · have hv := V2_small_n a a2 hs
    unfold noiseStatusOf
    rw [hv]
    exact ⟨fun _ => hs, fun _ => rfl⟩
  · have hv := verdict_not_small a a2 hs
    constructor
    · intro h
      unfold noiseStatusOf at h
      rcases V1_cases a a2 with h1 | h1 | h1 | h1
      · exact absurd h1 hv
      · rw [h1] at h
        exact absurd h (by decide)
      · rw [h1] at h
        exact absurd h (by decide)
      · rw [h1] at h
        exact absurd h (by decide)
    · intro h
      exact absurd h hs

theorem V6_floor_too_high_iff [DiffOracle] (a a2 : Counts) :
    noiseStatusOf a a2 = .noiseFloorTooHigh ↔
      (verdictOf a a2 = .firstHigher ∨ verdictOf a a2 = .firstLower) := by
  rcases V1_cases a a2 with h | h | h | h <;> simp [noiseStatusOf, h]

theorem V6_ok_iff [DiffOracle] (a a2 : Counts) :
    noiseStatusOf a a2 = .noiseOk ↔ verdictOf a a2 = .inconclusive := by
  rcases V1_cases a a2 with h | h | h | h <;> simp [noiseStatusOf, h]

theorem V6_identical_pair_never_too_high [DiffOracle] (c : Counts) :
    noiseStatusOf c c ≠ .noiseFloorTooHigh := by
  obtain ⟨h1, h2⟩ := V4_identical_counts c
  intro h
  rcases (V6_floor_too_high_iff c c).mp h with h3 | h3
  · exact h1 h3
  · exact h2 h3

def effectOf : NoiseStatus → Verdict → EffectResult
  | .noiseUnmeasured, _ => .invalid
  | .noiseFloorTooHigh, _ => .invalid
  | .noiseOk, .inconclusiveSmallN => .notEnoughRuns
  | .noiseOk, .firstHigher => .ruleLowersViolations
  | .noiseOk, .firstLower => .ruleRaisesViolations
  | .noiseOk, .inconclusive => .noMeasurableEffect

theorem E1_unmeasured_invalid (v : Verdict) : effectOf .noiseUnmeasured v = .invalid := by
  cases v <;> rfl

theorem E1_too_high_invalid (v : Verdict) : effectOf .noiseFloorTooHigh v = .invalid := by
  cases v <;> rfl

theorem E1_ok_small_n : effectOf .noiseOk .inconclusiveSmallN = .notEnoughRuns := rfl

theorem E1_ok_first_higher : effectOf .noiseOk .firstHigher = .ruleLowersViolations := rfl

theorem E1_ok_first_lower : effectOf .noiseOk .firstLower = .ruleRaisesViolations := rfl

theorem E1_ok_inconclusive : effectOf .noiseOk .inconclusive = .noMeasurableEffect := rfl

theorem E1_not_ok_invalid (n : NoiseStatus) (v : Verdict) (h : n ≠ .noiseOk) :
    effectOf n v = .invalid := by
  cases n
  · exact E1_unmeasured_invalid v
  · exact E1_too_high_invalid v
  · exact absurd rfl h

theorem E1_invalid_only_when_not_ok (n : NoiseStatus) (v : Verdict)
    (h : effectOf n v = .invalid) : n ≠ .noiseOk := by
  intro hn
  subst hn
  cases v <;> exact absurd h (by decide)

theorem E1_not_ok_loaded_cannot_decide (n : NoiseStatus) (v : Verdict) (g : GuardResult)
    (h : n ≠ .noiseOk) : decideRule .loaded (effectOf n v) g = .cannotDecide := by
  rw [E1_not_ok_invalid n v h]
  exact D3_loaded_invalid_cannot_decide g

theorem E1_not_ok_never_effect_decision (n : NoiseStatus) (v : Verdict) (r : Reach)
    (g : GuardResult) (h : n ≠ .noiseOk) :
    decideRule r (effectOf n v) g = .fixLoading ∨ decideRule r (effectOf n v) g = .cannotDecide := by
  rw [E1_not_ok_invalid n v h]
  cases r
  · right
    exact D3_loaded_invalid_cannot_decide g
  · left
    exact D1_masked_fix_loading _ g
  · right
    exact D2_unknown_cannot_decide _ g

theorem E1_exhaustive :
    ∀ n ∈ allNoise, ∀ v ∈ allVerdict,
      (n ≠ .noiseOk → effectOf n v = .invalid) ∧ (n = .noiseOk → effectOf n v ≠ .invalid) := by
  decide

def effectFromCounts [DiffOracle] (noiseA noiseB loo rule : Counts) : EffectResult :=
  effectOf (noiseStatusOf noiseA noiseB) (verdictOf loo rule)

structure PlanFacts where
  hasNoisePair : Bool
  noise : NoiseStatus
  looProbe : Reach
  ruleReach : Reach

def CanReport (p : PlanFacts) : Prop :=
  p.hasNoisePair = true ∧ p.noise = .noiseOk ∧ LooValid p.looProbe ∧ p.ruleReach ≠ .unknown

instance (p : PlanFacts) : Decidable (CanReport p) := by
  unfold CanReport LooValid
  exact inferInstance

def allPlanFacts : List PlanFacts :=
  [false, true].flatMap fun hasNoisePair =>
    allNoise.flatMap fun noise =>
      allReach.flatMap fun looProbe => allReach.map fun ruleReach => ⟨hasNoisePair, noise, looProbe, ruleReach⟩

theorem CanReport_flags (p : PlanFacts) :
    decide (CanReport p) = (p.hasNoisePair && decide (p.noise = .noiseOk) &&
      decide (p.looProbe = .loaded) && !decide (p.ruleReach = .unknown)) := by
  unfold CanReport LooValid
  cases p with
  | mk hasNoisePair noise looProbe ruleReach =>
    cases hasNoisePair <;> cases noise <;> cases looProbe <;> cases ruleReach <;> decide

theorem CanReport_exhaustive :
    allPlanFacts.length = 54 ∧ (allPlanFacts.filter fun p => decide (CanReport p)).length = 2 := by
  decide

def Reported (p : PlanFacts) (e : EffectResult) : Prop :=
  CanReport p ∧ ∃ v, e = effectOf p.noise v

theorem V6_no_effect_unless_noise_ok (p : PlanFacts) (e : EffectResult)
    (h : Reported p e) : p.noise = .noiseOk := h.1.2.1

theorem L8_no_noise_pair_no_effect (p : PlanFacts) (h : p.hasNoisePair = false) (e : EffectResult) :
    ¬ Reported p e := by
  intro hr
  have h1 := hr.1.1
  rw [h] at h1
  exact absurd h1 (by decide)

theorem L8_noise_not_ok_no_effect (p : PlanFacts) (h : p.noise ≠ .noiseOk) (e : EffectResult) :
    ¬ Reported p e := fun hr => h hr.1.2.1

theorem P4_loo_invalid_no_effect (p : PlanFacts) (h : ¬ LooValid p.looProbe) (e : EffectResult) :
    ¬ Reported p e := fun hr => h hr.1.2.2.1

theorem L7_unknown_rule_arm_no_effect (p : PlanFacts) (h : p.ruleReach = .unknown)
    (e : EffectResult) : ¬ Reported p e := fun hr => hr.1.2.2.2 h

theorem Reported_is_never_invalid (p : PlanFacts) (e : EffectResult) (h : Reported p e) :
    e ≠ .invalid := by
  obtain ⟨hc, v, hv⟩ := h
  have hn : p.noise = .noiseOk := hc.2.1
  rw [hv, hn]
  cases v <;> decide

end Willitharness
