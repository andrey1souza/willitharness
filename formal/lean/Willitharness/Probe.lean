import Willitharness.Decision

namespace Willitharness

def MinProbeRuns : Nat := 3

def probeResult (runs targetHits controlHits : Nat) : Reach :=
  if runs < MinProbeRuns then .unknown
  else if 0 < controlHits then .unknown
  else if targetHits = runs then .loaded
  else if targetHits = 0 then .masked
  else .unknown

theorem P1_few_runs_unknown (runs t c : Nat) (h : runs < MinProbeRuns) :
    probeResult runs t c = .unknown := by
  unfold probeResult
  rw [ite_eq_left h]

theorem P2_control_hit_unknown (runs t c : Nat) (h : 0 < c) :
    probeResult runs t c = .unknown := by
  unfold probeResult
  by_cases hr : runs < MinProbeRuns
  · rw [ite_eq_left hr]
  · rw [ite_eq_right hr, ite_eq_left h]

theorem P3_all_hit_loaded (runs t c : Nat) (hr : MinProbeRuns ≤ runs) (hc : c = 0) (ht : t = runs) :
    probeResult runs t c = .loaded := by
  have hr' : ¬ runs < MinProbeRuns := Nat.not_lt.mpr hr
  have hc' : ¬ 0 < c := by omega
  unfold probeResult
  rw [ite_eq_right hr', ite_eq_right hc', ite_eq_left ht]

theorem P3_none_hit_masked (runs t c : Nat) (hr : MinProbeRuns ≤ runs) (hc : c = 0) (ht : t = 0) :
    probeResult runs t c = .masked := by
  have hr' : ¬ runs < MinProbeRuns := Nat.not_lt.mpr hr
  have hc' : ¬ 0 < c := by omega
  have hne : ¬ t = runs := by
    simp only [MinProbeRuns] at hr
    omega
  unfold probeResult
  rw [ite_eq_right hr', ite_eq_right hc', ite_eq_right hne, ite_eq_left ht]

theorem P3_some_hit_unknown (runs t c : Nat) (hr : MinProbeRuns ≤ runs) (hc : c = 0)
    (h0 : 0 < t) (h1 : t < runs) : probeResult runs t c = .unknown := by
  have hr' : ¬ runs < MinProbeRuns := Nat.not_lt.mpr hr
  have hc' : ¬ 0 < c := by omega
  have hne : ¬ t = runs := by omega
  have hz : ¬ t = 0 := by omega
  unfold probeResult
  rw [ite_eq_right hr', ite_eq_right hc', ite_eq_right hne, ite_eq_right hz]

theorem P3_loaded_iff (runs t c : Nat) :
    probeResult runs t c = .loaded ↔ (MinProbeRuns ≤ runs ∧ c = 0 ∧ t = runs) := by
  constructor
  · intro h
    unfold probeResult at h
    by_cases a : runs < MinProbeRuns
    · rw [ite_eq_left a] at h
      exact absurd h (by decide)
    · by_cases b : 0 < c
      · rw [ite_eq_right a, ite_eq_left b] at h
        exact absurd h (by decide)
      · by_cases d : t = runs
        · exact ⟨Nat.not_lt.mp a, by omega, d⟩
        · by_cases e : t = 0
          · rw [ite_eq_right a, ite_eq_right b, ite_eq_right d, ite_eq_left e] at h
            exact absurd h (by decide)
          · rw [ite_eq_right a, ite_eq_right b, ite_eq_right d, ite_eq_right e] at h
            exact absurd h (by decide)
  · rintro ⟨hr, hc, ht⟩
    exact P3_all_hit_loaded runs t c hr hc ht

theorem P3_masked_iff (runs t c : Nat) :
    probeResult runs t c = .masked ↔ (MinProbeRuns ≤ runs ∧ c = 0 ∧ t = 0) := by
  constructor
  · intro h
    unfold probeResult at h
    by_cases a : runs < MinProbeRuns
    · rw [ite_eq_left a] at h
      exact absurd h (by decide)
    · by_cases b : 0 < c
      · rw [ite_eq_right a, ite_eq_left b] at h
        exact absurd h (by decide)
      · by_cases d : t = runs
        · rw [ite_eq_right a, ite_eq_right b, ite_eq_left d] at h
          exact absurd h (by decide)
        · by_cases e : t = 0
          · exact ⟨Nat.not_lt.mp a, by omega, e⟩
          · rw [ite_eq_right a, ite_eq_right b, ite_eq_right d, ite_eq_right e] at h
            exact absurd h (by decide)
  · rintro ⟨hr, hc, ht⟩
    exact P3_none_hit_masked runs t c hr hc ht

def LooValid (looProbe : Reach) : Prop := looProbe = .loaded

theorem P4_valid_iff (runs nonTargetHits controlHits : Nat) :
    LooValid (probeResult runs nonTargetHits controlHits) ↔
      (MinProbeRuns ≤ runs ∧ controlHits = 0 ∧ nonTargetHits = runs) :=
  P3_loaded_iff runs nonTargetHits controlHits

theorem P4_masked_probe_invalidates (runs nonTargetHits controlHits : Nat)
    (h : probeResult runs nonTargetHits controlHits = .masked) :
    ¬ LooValid (probeResult runs nonTargetHits controlHits) := by
  unfold LooValid
  rw [h]
  decide

theorem probe_masked_fix_loading (runs t c : Nat) (e : EffectResult) (g : GuardResult)
    (h : probeResult runs t c = .masked) : decideRule (probeResult runs t c) e g = .fixLoading := by
  rw [h]
  exact D1_masked_fix_loading e g

theorem probe_unknown_cannot_decide (runs t c : Nat) (e : EffectResult) (g : GuardResult)
    (h : probeResult runs t c = .unknown) : decideRule (probeResult runs t c) e g = .cannotDecide := by
  rw [h]
  exact D2_unknown_cannot_decide e g

end Willitharness
