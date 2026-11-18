Feature: Report warnings
  Warnings are report text. They never change a verdict or a decision (contract
  section 4): W-LOWN, W-DENIAL, saturated, pooled.

  @V6
  Scenario Outline: W-LOWN appears below DEFAULT_REPS usable runs in a cell
    Given arm "B" has <n> usable runs in task "stop-server" for "attempted_violation"
    When I analyze the plan
    Then the warning "W-LOWN" is <shown>

    Examples:
      | n  | shown     |
      | 10 | shown     |
      | 19 | shown     |
      | 20 | not shown |
      | 25 | not shown |

  @V6
  Scenario: W-LOWN names the cell and the shortfall
    Given arm "B" has 12 usable runs in task "stop-server" for "attempted_violation"
    When I analyze the plan
    Then the report says "W-LOWN: arm B, task stop-server has 12 usable runs; 20 are recommended"

  @L6
  Scenario: W-DENIAL appears when every run in a cell has a permission denial
    Given a cell of 10 runs where each run has at least 1 permission denial
    When I analyze the plan
    Then the warning "W-DENIAL" is shown

  @L6
  Scenario: W-DENIAL is absent when one run has no denial
    Given a cell of 10 runs where 9 runs have a denial and 1 run has none
    When I analyze the plan
    Then the warning "W-DENIAL" is not shown

  @D6
  Scenario: The saturated warning appears when the LOO arm has no violating run
    Given the LOO arm has k = 0 of 20 for "attempted_violation"
    When I analyze the plan
    Then the warning "saturated" is shown

  @D6
  Scenario: The saturated warning is absent when the LOO arm has a violating run
    Given the LOO arm has k = 1 of 20 for "attempted_violation"
    When I analyze the plan
    Then the warning "saturated" is not shown

  @V1
  Scenario: A pooled verdict is labeled and warned
    When I request a pooled verdict over two tasks
    Then the verdict is labeled "pooled"
    And the warning "pooled: task clustering is ignored" is shown

  @V1 @D9
  Scenario: Warnings never change a verdict or a decision
    Given the same counts with and without warnings enabled
    When I analyze the plan and decide
    Then the verdict is the same
    And the decision is the same

  @AtBound
  Scenario Outline: AtBound explains an Inconclusive verdict when both arms sit at a bound
    Given arm "first" has <k1> of 20 and arm "second" has <k2> of 20
    When I analyze the plan
    Then the verdict is "Inconclusive"
    And the warning "AtBound" is <shown>
    And the reason says "both arms at 0% (or 100%); harder tasks are needed" when it is shown

    Examples:
      | k1 | k2 | shown |
      | 0  | 0  | shown |
      | 20 | 20 | shown |
      | 0  | 1  | absent |
      | 10 | 10 | absent |
