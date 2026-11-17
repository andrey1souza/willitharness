namespace Willitharness

structure Counts where
  k : Nat
  n : Nat
  deriving DecidableEq, Repr

def Counts.Valid (c : Counts) : Prop := 1 ≤ c.n ∧ c.k ≤ c.n

def Counts.rate (c : Counts) : Rat := (c.k : Rat) / (c.n : Rat)

def MinRuns : Nat := 5

inductive Verdict where
  | inconclusiveSmallN
  | firstHigher
  | firstLower
  | inconclusive
  deriving DecidableEq, Repr

def Verdict.flip : Verdict → Verdict
  | .firstHigher => .firstLower
  | .firstLower => .firstHigher
  | .inconclusiveSmallN => .inconclusiveSmallN
  | .inconclusive => .inconclusive

theorem Verdict.flip_involutive (v : Verdict) : v.flip.flip = v := by
  cases v <;> rfl

class DiffOracle where
  diff : Counts → Counts → Rat × Rat
  diff_ordered : ∀ a b, (diff a b).1 ≤ (diff a b).2
  diff_swap : ∀ a b, diff b a = (-(diff a b).2, -(diff a b).1)

class WilsonOracle where
  wilson : Counts → Rat × Rat
  wilson_bounds : ∀ c : Counts, c.Valid →
    0 ≤ (wilson c).1 ∧ (wilson c).1 ≤ c.rate ∧ c.rate ≤ (wilson c).2 ∧ (wilson c).2 ≤ 1

@[instance_reducible]
def zeroOracle : DiffOracle where
  diff _ _ := (0, 0)
  diff_ordered _ _ := Rat.le_refl
  diff_swap _ _ := by rw [Rat.neg_zero]

theorem diffOracle_nonvacuous : Nonempty DiffOracle := ⟨zeroOracle⟩

def verdictOf [DiffOracle] (a b : Counts) : Verdict :=
  if min a.n b.n < MinRuns then .inconclusiveSmallN
  else if 0 < (DiffOracle.diff a b).1 then .firstHigher
  else if (DiffOracle.diff a b).2 < 0 then .firstLower
  else .inconclusive

theorem neg_pos_iff (x : Rat) : 0 < -x ↔ x < 0 := by
  constructor
  · intro h
    have h2 := Rat.neg_lt_neg h
    rwa [Rat.neg_neg, Rat.neg_zero] at h2
  · intro h
    have h2 := Rat.neg_lt_neg h
    rwa [Rat.neg_zero] at h2

theorem neg_lt_zero_iff (x : Rat) : -x < 0 ↔ 0 < x := by
  constructor
  · intro h
    have h2 := Rat.neg_lt_neg h
    rwa [Rat.neg_zero, Rat.neg_neg] at h2
  · intro h
    have h2 := Rat.neg_lt_neg h
    rwa [Rat.neg_zero] at h2

theorem pos_excludes_neg {lo hi : Rat} (ord : lo ≤ hi) (p : 0 < lo) : ¬ hi < 0 := by
  intro q
  exact (Rat.not_le.mpr p) (Rat.le_trans ord (Rat.le_of_lt q))

theorem diffSelf_derived [DiffOracle] (a : Counts) :
    (DiffOracle.diff a a).1 ≤ 0 ∧ 0 ≤ (DiffOracle.diff a a).2 := by
  have hs := DiffOracle.diff_swap a a
  have h1 : (DiffOracle.diff a a).1 = -(DiffOracle.diff a a).2 := congrArg Prod.fst hs
  have h2 : (DiffOracle.diff a a).2 = -(DiffOracle.diff a a).1 := congrArg Prod.snd hs
  have ord := DiffOracle.diff_ordered a a
  constructor
  · apply Rat.not_lt.mp
    intro p
    have q : (DiffOracle.diff a a).2 < 0 := by
      rw [h2]
      exact (neg_lt_zero_iff _).mpr p
    exact pos_excludes_neg ord p q
  · apply Rat.not_lt.mp
    intro q
    have p : 0 < (DiffOracle.diff a a).1 := by
      rw [h1]
      exact (neg_pos_iff _).mpr q
    exact pos_excludes_neg ord p q

theorem V5_interval_bounds [WilsonOracle] (c : Counts) (h : c.Valid) :
    0 ≤ (WilsonOracle.wilson c).1 ∧ (WilsonOracle.wilson c).1 ≤ c.rate ∧
      c.rate ≤ (WilsonOracle.wilson c).2 ∧ (WilsonOracle.wilson c).2 ≤ 1 :=
  WilsonOracle.wilson_bounds c h

theorem V1_exactly_one [DiffOracle] (a b : Counts) :
    ∃ v, verdictOf a b = v ∧ ∀ w, verdictOf a b = w → w = v :=
  ⟨verdictOf a b, rfl, fun _ h => h.symm⟩

theorem V1_cases [DiffOracle] (a b : Counts) :
    verdictOf a b = .inconclusiveSmallN ∨ verdictOf a b = .firstHigher ∨
      verdictOf a b = .firstLower ∨ verdictOf a b = .inconclusive := by
  cases h : verdictOf a b <;> simp

theorem V1_pairwise_distinct :
    Verdict.inconclusiveSmallN ≠ Verdict.firstHigher ∧
    Verdict.inconclusiveSmallN ≠ Verdict.firstLower ∧
    Verdict.inconclusiveSmallN ≠ Verdict.inconclusive ∧
    Verdict.firstHigher ≠ Verdict.firstLower ∧
    Verdict.firstHigher ≠ Verdict.inconclusive ∧
    Verdict.firstLower ≠ Verdict.inconclusive := by
  decide

theorem V2_small_n [DiffOracle] (a b : Counts) (h : min a.n b.n < MinRuns) :
    verdictOf a b = .inconclusiveSmallN := by
  unfold verdictOf
  rw [ite_eq_left h]

theorem swap_core (lo hi : Rat) (ord : lo ≤ hi) :
    (if 0 < lo then Verdict.firstHigher else if hi < 0 then .firstLower else .inconclusive)
      = (if 0 < -hi then Verdict.firstHigher else if -lo < 0 then .firstLower else .inconclusive).flip := by
  by_cases p : 0 < lo
  · have n1 : ¬ 0 < -hi := fun h => pos_excludes_neg ord p ((neg_pos_iff hi).mp h)
    have n2 : -lo < 0 := (neg_lt_zero_iff lo).mpr p
    rw [ite_eq_left p, ite_eq_right n1, ite_eq_left n2]
    rfl
  · by_cases q : hi < 0
    · have m1 : 0 < -hi := (neg_pos_iff hi).mpr q
      rw [ite_eq_right p, ite_eq_left q, ite_eq_left m1]
      rfl
    · have m1 : ¬ 0 < -hi := fun h => q ((neg_pos_iff hi).mp h)
      have m2 : ¬ -lo < 0 := fun h => p ((neg_lt_zero_iff lo).mp h)
      rw [ite_eq_right p, ite_eq_right q, ite_eq_right m1, ite_eq_right m2]
      rfl

theorem V3_swap_symmetry [DiffOracle] (a b : Counts) :
    verdictOf a b = (verdictOf b a).flip := by
  have hswap := DiffOracle.diff_swap a b
  have hord := DiffOracle.diff_ordered a b
  by_cases hs : min a.n b.n < MinRuns
  · have hs' : min b.n a.n < MinRuns := by rw [Nat.min_comm]; exact hs
    unfold verdictOf
    rw [ite_eq_left hs, ite_eq_left hs']
    rfl
  · have hs' : ¬ min b.n a.n < MinRuns := by rw [Nat.min_comm]; exact hs
    unfold verdictOf
    rw [ite_eq_right hs, ite_eq_right hs', hswap]
    exact swap_core _ _ hord

theorem V4_identical_counts [DiffOracle] (c : Counts) :
    verdictOf c c ≠ .firstHigher ∧ verdictOf c c ≠ .firstLower := by
  obtain ⟨h1, h2⟩ := diffSelf_derived c
  have n1 : ¬ 0 < (DiffOracle.diff c c).1 := Rat.not_lt.mpr h1
  have n2 : ¬ (DiffOracle.diff c c).2 < 0 := Rat.not_lt.mpr h2
  unfold verdictOf
  by_cases hs : min c.n c.n < MinRuns
  · rw [ite_eq_left hs]
    exact ⟨by decide, by decide⟩
  · rw [ite_eq_right hs, ite_eq_right n1, ite_eq_right n2]
    exact ⟨by decide, by decide⟩

end Willitharness
