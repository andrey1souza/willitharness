import Willitharness.Link

namespace Willitharness

inductive ContentVerdict where
  | contentBeatsFiller
  | addedTextHelps
  | nothingHelps
  | fillerBeatsContent
  | unclear
  | noRoomToHelp
  | inconclusive
  deriving DecidableEq, Repr

def ContentVerdict.name : ContentVerdict → String
  | .contentBeatsFiller => "ContentBeatsFiller"
  | .addedTextHelps => "AddedTextHelps"
  | .nothingHelps => "NothingHelps"
  | .fillerBeatsContent => "FillerBeatsContent"
  | .unclear => "Unclear"
  | .noRoomToHelp => "NoRoomToHelp"
  | .inconclusive => "Inconclusive"

def contentVerdict : Verdict → Verdict → Verdict → Bool → ContentVerdict
  | .inconclusiveSmallN, _, _, _ => .inconclusive
  | _, .inconclusiveSmallN, _, _ => .inconclusive
  | _, _, .inconclusiveSmallN, _ => .inconclusive
  | _, _, _, true => .noRoomToHelp
  | .firstHigher, _, _, false => .contentBeatsFiller
  | .firstLower, _, _, false => .fillerBeatsContent
  | .inconclusive, .firstHigher, .firstHigher, false => .addedTextHelps
  | .inconclusive, .firstHigher, _, false => .unclear
  | .inconclusive, _, .firstHigher, false => .unclear
  | .inconclusive, _, _, false => .nothingHelps

def allContentInputs : List (Verdict × Verdict × Verdict × Bool) :=
  allVerdict.flatMap fun p => allVerdict.flatMap fun n => allVerdict.flatMap fun c =>
    [false, true].map fun clean => (p, n, c, clean)

theorem PB1_total (p n c : Verdict) (clean : Bool) :
    ∃ v, contentVerdict p n c clean = v := ⟨_, rfl⟩

theorem PB1_deterministic (p n c : Verdict) (clean : Bool) (v1 v2 : ContentVerdict)
    (h1 : contentVerdict p n c clean = v1) (h2 : contentVerdict p n c clean = v2) : v1 = v2 := by
  rw [← h1, ← h2]

set_option maxRecDepth 4000 in
theorem PB1_allContentInputs_length : allContentInputs.length = 128 := by decide

theorem PB1_allContentInputs_complete (p n c : Verdict) (clean : Bool) :
    (p, n, c, clean) ∈ allContentInputs := by
  cases p <;> cases n <;> cases c <;> cases clean <;> decide

theorem PB2_small_n_inconclusive (p n c : Verdict) (clean : Bool)
    (h : p = .inconclusiveSmallN ∨ n = .inconclusiveSmallN ∨ c = .inconclusiveSmallN) :
    contentVerdict p n c clean = .inconclusive := by
  cases p <;> cases n <;> cases c <;> cases clean <;> simp_all [contentVerdict]

theorem PB3_no_room_iff (p n c : Verdict) (clean : Bool) :
    contentVerdict p n c clean = .noRoomToHelp ↔
      clean = true ∧ p ≠ .inconclusiveSmallN ∧ n ≠ .inconclusiveSmallN ∧ c ≠ .inconclusiveSmallN := by
  cases p <;> cases n <;> cases c <;> cases clean <;> simp [contentVerdict]

theorem PB4_content_beats_filler_iff (p n c : Verdict) (clean : Bool) :
    contentVerdict p n c clean = .contentBeatsFiller ↔
      p = .firstHigher ∧ n ≠ .inconclusiveSmallN ∧ c ≠ .inconclusiveSmallN ∧ clean = false := by
  cases p <;> cases n <;> cases c <;> cases clean <;> simp [contentVerdict]

theorem PB5_filler_beats_content_iff (p n c : Verdict) (clean : Bool) :
    contentVerdict p n c clean = .fillerBeatsContent ↔
      p = .firstLower ∧ n ≠ .inconclusiveSmallN ∧ c ≠ .inconclusiveSmallN ∧ clean = false := by
  cases p <;> cases n <;> cases c <;> cases clean <;> simp [contentVerdict]

theorem PB6_added_text_helps_when_equal_to_filler_and_both_beat_nothing :
    contentVerdict .inconclusive .firstHigher .firstHigher false = .addedTextHelps := rfl

theorem PB6_added_text_helps_only_then (p n c : Verdict) (clean : Bool)
    (h : contentVerdict p n c clean = .addedTextHelps) :
    p = .inconclusive ∧ n = .firstHigher ∧ c = .firstHigher ∧ clean = false := by
  cases p <;> cases n <;> cases c <;> cases clean <;> simp_all [contentVerdict]

theorem PB7_nothing_helps_when_equal_to_filler_and_neither_beats_nothing (n c : Verdict)
    (hn : n = .inconclusive ∨ n = .firstLower) (hc : c = .inconclusive ∨ c = .firstLower) :
    contentVerdict .inconclusive n c false = .nothingHelps := by
  rcases hn with rfl | rfl <;> rcases hc with rfl | rfl <;> rfl

theorem PB7_nothing_helps_only_then (p n c : Verdict) (clean : Bool)
    (h : contentVerdict p n c clean = .nothingHelps) :
    p = .inconclusive ∧ (n = .inconclusive ∨ n = .firstLower) ∧
      (c = .inconclusive ∨ c = .firstLower) ∧ clean = false := by
  cases p <;> cases n <;> cases c <;> cases clean <;> simp_all [contentVerdict]

theorem PB8_unclear_when_only_the_component_beats_nothing :
    contentVerdict .inconclusive .inconclusive .firstHigher false = .unclear := rfl

theorem PB8_unclear_when_only_the_filler_beats_nothing :
    contentVerdict .inconclusive .firstHigher .inconclusive false = .unclear := rfl

theorem PB8_unclear_only_then (p n c : Verdict) (clean : Bool)
    (h : contentVerdict p n c clean = .unclear) :
    p = .inconclusive ∧ clean = false ∧ n ≠ .inconclusiveSmallN ∧ c ≠ .inconclusiveSmallN ∧
      ((n = .firstHigher) ≠ (c = .firstHigher)) := by
  cases p <;> cases n <;> cases c <;> cases clean <;> simp_all [contentVerdict]

end Willitharness
