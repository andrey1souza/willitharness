import Willitharness.Link

namespace Willitharness

inductive ArmVerdict where
  | keepComponent
  | replaceWithPrompt
  | deleteCandidate
  | inconclusive
  | insuranceKeep
  deriving DecidableEq, Repr

def ArmVerdict.name : ArmVerdict → String
  | .keepComponent => "KeepComponent"
  | .replaceWithPrompt => "ReplaceWithPrompt"
  | .deleteCandidate => "DeleteCandidate"
  | .inconclusive => "Inconclusive"
  | .insuranceKeep => "InsuranceKeep"

def threeArmVerdict : Verdict → Verdict → Bool → ArmVerdict
  | .inconclusiveSmallN, _, _ => .inconclusive
  | _, .inconclusiveSmallN, _ => .inconclusive
  | _, _, true => .insuranceKeep
  | .firstHigher, _, false => .keepComponent
  | .firstLower, _, false => .inconclusive
  | .inconclusive, .firstHigher, false => .replaceWithPrompt
  | .inconclusive, .inconclusive, false => .deleteCandidate
  | .inconclusive, .firstLower, false => .inconclusive

def allArmInputs : List (Verdict × Verdict × Bool) :=
  allVerdict.flatMap fun p => allVerdict.flatMap fun n => [false, true].map fun clean => (p, n, clean)

theorem TA1_total (p n : Verdict) (clean : Bool) :
    ∃ v, threeArmVerdict p n clean = v := ⟨_, rfl⟩

theorem TA1_deterministic (p n : Verdict) (clean : Bool) (v1 v2 : ArmVerdict)
    (h1 : threeArmVerdict p n clean = v1) (h2 : threeArmVerdict p n clean = v2) : v1 = v2 := by
  rw [← h1, ← h2]

theorem TA1_allArmInputs_length : allArmInputs.length = 32 := by decide

theorem TA1_allArmInputs_complete (p n : Verdict) (clean : Bool) :
    (p, n, clean) ∈ allArmInputs := by
  cases p <;> cases n <;> cases clean <;> decide

theorem TA2_small_n_inconclusive (p n : Verdict) (clean : Bool)
    (h : p = .inconclusiveSmallN ∨ n = .inconclusiveSmallN) :
    threeArmVerdict p n clean = .inconclusive := by
  cases p <;> cases n <;> cases clean <;> simp_all [threeArmVerdict]

theorem TA3_insurance_iff (p n : Verdict) (clean : Bool) :
    threeArmVerdict p n clean = .insuranceKeep ↔
      clean = true ∧ p ≠ .inconclusiveSmallN ∧ n ≠ .inconclusiveSmallN := by
  cases p <;> cases n <;> cases clean <;> simp [threeArmVerdict]

theorem TA4_keep_only_when_component_beats_prompt (p n : Verdict) (clean : Bool)
    (h : threeArmVerdict p n clean = .keepComponent) :
    p = .firstHigher ∧ n ≠ .inconclusiveSmallN ∧ clean = false := by
  cases p <;> cases n <;> cases clean <;> simp_all [threeArmVerdict]

theorem TA4_keep_when_component_beats_prompt (n : Verdict) (h : n ≠ .inconclusiveSmallN) :
    threeArmVerdict .firstHigher n false = .keepComponent := by
  cases n <;> simp_all [threeArmVerdict]

theorem TA5_replace_when_equal_to_prompt_and_beats_nothing :
    threeArmVerdict .inconclusive .firstHigher false = .replaceWithPrompt := rfl

theorem TA5_replace_only_then (p n : Verdict) (clean : Bool)
    (h : threeArmVerdict p n clean = .replaceWithPrompt) :
    p = .inconclusive ∧ n = .firstHigher ∧ clean = false := by
  cases p <;> cases n <;> cases clean <;> simp_all [threeArmVerdict]

theorem TA6_delete_when_equal_to_nothing :
    threeArmVerdict .inconclusive .inconclusive false = .deleteCandidate := rfl

theorem TA6_delete_only_then (p n : Verdict) (clean : Bool)
    (h : threeArmVerdict p n clean = .deleteCandidate) :
    p = .inconclusive ∧ n = .inconclusive ∧ clean = false := by
  cases p <;> cases n <;> cases clean <;> simp_all [threeArmVerdict]

theorem TA7_component_worse_than_prompt_inconclusive (n : Verdict) (clean : Bool) :
    threeArmVerdict .firstLower n clean ≠ .keepComponent ∧
      threeArmVerdict .firstLower n clean ≠ .replaceWithPrompt ∧
      threeArmVerdict .firstLower n clean ≠ .deleteCandidate := by
  cases n <;> cases clean <;> simp [threeArmVerdict]

theorem TA7_component_worse_than_nothing_inconclusive :
    threeArmVerdict .inconclusive .firstLower false = .inconclusive := rfl

end Willitharness
