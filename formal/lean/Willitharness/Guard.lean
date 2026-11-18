import Willitharness.Verdict
import Willitharness.Decision

namespace Willitharness

inductive Coverage where
  | full
  | partly
  | noneSeen
  deriving DecidableEq, Repr

def Coverage.name : Coverage → String
  | .full => "Full"
  | .partly => "Partial"
  | .noneSeen => "NoneSeen"

def allCoverage : List Coverage := [.full, .partly, .noneSeen]

def GuardConditions (completed : Verdict) (coverage : Coverage) (bypassRate : Rat) : Prop :=
  completed ≠ .firstLower ∧ completed ≠ .inconclusiveSmallN ∧ coverage = .full ∧ bypassRate = 0

instance (completed : Verdict) (coverage : Coverage) (bypassRate : Rat) :
    Decidable (GuardConditions completed coverage bypassRate) := by
  unfold GuardConditions
  exact inferInstance

def GuardEvidenceMissing (completed : Verdict) (coverage : Coverage) : Prop :=
  completed = .inconclusiveSmallN ∨ coverage = .noneSeen

instance (completed : Verdict) (coverage : Coverage) :
    Decidable (GuardEvidenceMissing completed coverage) := by
  unfold GuardEvidenceMissing
  exact inferInstance

def guardOf : Option Verdict → Coverage → Rat → GuardResult
  | none, _, _ => .guardUntested
  | some completed, coverage, bypassRate =>
    if GuardEvidenceMissing completed coverage then .guardUntested
    else if GuardConditions completed coverage bypassRate then .guardMatchesRule
    else .guardWorse

def guardOfBool : Option Verdict → Coverage → Bool → GuardResult
  | none, _, _ => .guardUntested
  | some completed, coverage, zeroBypass =>
    if GuardEvidenceMissing completed coverage then .guardUntested
    else if completed ≠ .firstLower ∧ coverage = .full ∧ zeroBypass = true then .guardMatchesRule
    else .guardWorse

theorem G1_bool_bridge (cv : Option Verdict) (cov : Coverage) (br : Rat) :
    guardOf cv cov br = guardOfBool cv cov (decide (br = 0)) := by
  cases cv with
  | none => rfl
  | some v =>
    simp only [guardOf, guardOfBool]
    by_cases hm : GuardEvidenceMissing v cov
    · simp [hm]
    · have h1 : v ≠ .inconclusiveSmallN := fun h => hm (Or.inl h)
      have h2 : cov ≠ .noneSeen := fun h => hm (Or.inr h)
      simp [hm, GuardConditions, h1]

theorem G1_untested_iff (cv : Option Verdict) (cov : Coverage) (br : Rat) :
    guardOf cv cov br = .guardUntested ↔
      cv = none ∨ cv = some .inconclusiveSmallN ∨ cov = .noneSeen := by
  cases cv with
  | none => simp [guardOf]
  | some v =>
    simp only [guardOf]
    by_cases hm : GuardEvidenceMissing v cov
    · have hr : v = .inconclusiveSmallN ∨ cov = .noneSeen := hm
      simp [hm, hr]
    · have h1 : v ≠ .inconclusiveSmallN := fun h => hm (Or.inl h)
      have h2 : cov ≠ .noneSeen := fun h => hm (Or.inr h)
      by_cases hc : GuardConditions v cov br
      · simp [hm, hc, h1, h2]
      · simp [hm, hc, h1, h2]

theorem G1_small_n_untested (cov : Coverage) (br : Rat) :
    guardOf (some .inconclusiveSmallN) cov br = .guardUntested := by
  simp [guardOf, GuardEvidenceMissing]

theorem G1_none_seen_untested (cv : Option Verdict) (br : Rat) :
    guardOf cv .noneSeen br = .guardUntested := by
  cases cv with
  | none => rfl
  | some v => simp [guardOf, GuardEvidenceMissing]

theorem G1_matches_iff (cv : Option Verdict) (cov : Coverage) (br : Rat) :
    guardOf cv cov br = .guardMatchesRule ↔
      ∃ v, cv = some v ∧ GuardConditions v cov br := by
  cases cv with
  | none => simp [guardOf]
  | some v =>
    constructor
    · intro h
      simp only [guardOf] at h
      by_cases hm : GuardEvidenceMissing v cov
      · simp [hm] at h
      · by_cases hc : GuardConditions v cov br
        · exact ⟨v, rfl, hc⟩
        · simp [hm, hc] at h
    · rintro ⟨w, hw, hc⟩
      cases hw
      have hm : ¬ GuardEvidenceMissing v cov := by
        intro h
        rcases h with h | h
        · exact hc.2.1 h
        · have hf : cov = .full := hc.2.2.1
          rw [hf] at h
          exact absurd h (by decide)
      simp [guardOf, hm, hc]

theorem G1_matches_implies_conditions (cv : Option Verdict) (cov : Coverage) (br : Rat)
    (h : guardOf cv cov br = .guardMatchesRule) :
    ∃ v, cv = some v ∧ v ≠ .firstLower ∧ v ≠ .inconclusiveSmallN ∧ cov = .full ∧ br = 0 := by
  obtain ⟨v, hv, hc⟩ := (G1_matches_iff cv cov br).mp h
  exact ⟨v, hv, hc⟩

theorem G1_bypass_blocks_match (cv : Option Verdict) (cov : Coverage) (br : Rat) (h : br ≠ 0) :
    guardOf cv cov br ≠ .guardMatchesRule := by
  intro hm
  obtain ⟨_, _, _, _, _, hb⟩ := G1_matches_implies_conditions cv cov br hm
  exact h hb

theorem G1_partial_coverage_blocks_match (cv : Option Verdict) (br : Rat) :
    guardOf cv .partly br ≠ .guardMatchesRule := by
  intro hm
  obtain ⟨_, _, _, _, hc, _⟩ := G1_matches_implies_conditions cv .partly br hm
  exact absurd hc (by decide)

theorem G1_first_lower_blocks_match (cov : Coverage) (br : Rat) :
    guardOf (some .firstLower) cov br ≠ .guardMatchesRule := by
  intro hm
  obtain ⟨v, hv, h1, _⟩ := G1_matches_implies_conditions (some .firstLower) cov br hm
  cases hv
  exact h1 rfl

theorem G1_small_n_blocks_match (cov : Coverage) (br : Rat) :
    guardOf (some .inconclusiveSmallN) cov br ≠ .guardMatchesRule := by
  rw [G1_small_n_untested]
  decide

theorem G1_D7_only_if_conditions (r : Reach) (e : EffectResult) (cv : Option Verdict)
    (cov : Coverage) (br : Rat)
    (h : decideRule r e (guardOf cv cov br) = .replaceWithGuard) :
    r = .loaded ∧ e = .ruleLowersViolations ∧
      ∃ v, cv = some v ∧ v ≠ .firstLower ∧ v ≠ .inconclusiveSmallN ∧ cov = .full ∧ br = 0 := by
  obtain ⟨hr, he, hg⟩ := D10_replace_only_when_justified r e (guardOf cv cov br) h
  exact ⟨hr, he, G1_matches_implies_conditions cv cov br hg⟩

theorem G1_D7_fires (v : Verdict) (cov : Coverage) (br : Rat) (hc : GuardConditions v cov br) :
    decideRule .loaded .ruleLowersViolations (guardOf (some v) cov br) = .replaceWithGuard := by
  have hg : guardOf (some v) cov br = .guardMatchesRule :=
    (G1_matches_iff (some v) cov br).mpr ⟨v, rfl, hc⟩
  rw [hg]
  exact D7_replace_with_guard

end Willitharness
