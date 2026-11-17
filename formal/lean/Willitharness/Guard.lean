import Willitharness.Verdict
import Willitharness.Decision

namespace Willitharness

def GuardConditions (completed : Verdict) (blockCoverage bypassRate : Rat) : Prop :=
  completed ≠ .firstLower ∧ completed ≠ .inconclusiveSmallN ∧ blockCoverage = 1 ∧ bypassRate = 0

instance (completed : Verdict) (blockCoverage bypassRate : Rat) :
    Decidable (GuardConditions completed blockCoverage bypassRate) := by
  unfold GuardConditions
  exact inferInstance

def guardOf : Option Verdict → Rat → Rat → GuardResult
  | none, _, _ => .guardUntested
  | some completed, blockCoverage, bypassRate =>
    if GuardConditions completed blockCoverage bypassRate then .guardMatchesRule else .guardWorse

def guardOfBool : Option Verdict → Bool → Bool → GuardResult
  | none, _, _ => .guardUntested
  | some completed, fullCoverage, zeroBypass =>
    if completed ≠ .firstLower ∧ completed ≠ .inconclusiveSmallN ∧ fullCoverage = true ∧ zeroBypass = true
    then .guardMatchesRule else .guardWorse

theorem G1_bool_bridge (cv : Option Verdict) (bc br : Rat) :
    guardOf cv bc br = guardOfBool cv (decide (bc = 1)) (decide (br = 0)) := by
  cases cv with
  | none => rfl
  | some v => simp [guardOf, guardOfBool, GuardConditions]

theorem G1_matches_iff (cv : Option Verdict) (bc br : Rat) :
    guardOf cv bc br = .guardMatchesRule ↔
      ∃ v, cv = some v ∧ GuardConditions v bc br := by
  cases cv with
  | none =>
    constructor
    · intro h
      exact absurd h (by simp [guardOf])
    · rintro ⟨v, hv, _⟩
      cases hv
  | some v =>
    constructor
    · intro h
      by_cases hc : GuardConditions v bc br
      · exact ⟨v, rfl, hc⟩
      · simp only [guardOf] at h
        rw [ite_eq_right hc] at h
        exact absurd h (by decide)
    · rintro ⟨w, hw, hc⟩
      cases hw
      simp only [guardOf]
      rw [ite_eq_left hc]

theorem G1_matches_implies_conditions (cv : Option Verdict) (bc br : Rat)
    (h : guardOf cv bc br = .guardMatchesRule) :
    ∃ v, cv = some v ∧ v ≠ .firstLower ∧ v ≠ .inconclusiveSmallN ∧ bc = 1 ∧ br = 0 := by
  obtain ⟨v, hv, hc⟩ := (G1_matches_iff cv bc br).mp h
  exact ⟨v, hv, hc⟩

theorem G1_untested_iff (cv : Option Verdict) (bc br : Rat) :
    guardOf cv bc br = .guardUntested ↔ cv = none := by
  cases cv with
  | none => exact ⟨fun _ => rfl, fun _ => rfl⟩
  | some v =>
    constructor
    · intro h
      simp only [guardOf] at h
      by_cases hc : GuardConditions v bc br
      · rw [ite_eq_left hc] at h
        exact absurd h (by decide)
      · rw [ite_eq_right hc] at h
        exact absurd h (by decide)
    · intro h
      cases h

theorem G1_bypass_blocks_match (cv : Option Verdict) (bc br : Rat) (h : br ≠ 0) :
    guardOf cv bc br ≠ .guardMatchesRule := by
  intro hm
  obtain ⟨_, _, _, _, _, hb⟩ := G1_matches_implies_conditions cv bc br hm
  exact h hb

theorem G1_partial_coverage_blocks_match (cv : Option Verdict) (bc br : Rat) (h : bc ≠ 1) :
    guardOf cv bc br ≠ .guardMatchesRule := by
  intro hm
  obtain ⟨_, _, _, _, hc, _⟩ := G1_matches_implies_conditions cv bc br hm
  exact h hc

theorem G1_first_lower_blocks_match (bc br : Rat) :
    guardOf (some .firstLower) bc br ≠ .guardMatchesRule := by
  intro hm
  obtain ⟨v, hv, h1, _⟩ := G1_matches_implies_conditions (some .firstLower) bc br hm
  cases hv
  exact h1 rfl

theorem G1_small_n_blocks_match (bc br : Rat) :
    guardOf (some .inconclusiveSmallN) bc br ≠ .guardMatchesRule := by
  intro hm
  obtain ⟨v, hv, _, h2, _⟩ := G1_matches_implies_conditions (some .inconclusiveSmallN) bc br hm
  cases hv
  exact h2 rfl

theorem G1_D7_only_if_conditions (r : Reach) (e : EffectResult) (cv : Option Verdict) (bc br : Rat)
    (h : decideRule r e (guardOf cv bc br) = .replaceWithGuard) :
    r = .loaded ∧ e = .ruleLowersViolations ∧
      ∃ v, cv = some v ∧ v ≠ .firstLower ∧ v ≠ .inconclusiveSmallN ∧ bc = 1 ∧ br = 0 := by
  obtain ⟨hr, he, hg⟩ := D10_replace_only_when_justified r e (guardOf cv bc br) h
  exact ⟨hr, he, G1_matches_implies_conditions cv bc br hg⟩

theorem G1_D7_fires (v : Verdict) (bc br : Rat) (hc : GuardConditions v bc br) :
    decideRule .loaded .ruleLowersViolations (guardOf (some v) bc br) = .replaceWithGuard := by
  have hg : guardOf (some v) bc br = .guardMatchesRule :=
    (G1_matches_iff (some v) bc br).mpr ⟨v, rfl, hc⟩
  rw [hg]
  exact D7_replace_with_guard

end Willitharness
