Feature: Decision table and effect mapping
  One decision per rule from reachability, effect and guard results (contract
  section 6). The effect result comes from the verdict and the noise status (E1).
  The table is a total function on 3 x 5 x 3 = 45 inputs.

  @D1
  Scenario Outline: A masked rule is always a loading problem
    Given reachability "Masked", effect "<effect>" and guard "<guard>"
    When I decide
    Then the decision is "FixLoading"

    Examples:
      | effect               | guard            |
      | RuleLowersViolations | GuardMatchesRule |
      | NoMeasurableEffect   | GuardUntested    |
      | Invalid              | GuardWorse       |
      | NotEnoughRuns        | GuardUntested    |

  @D2
  Scenario Outline: An unknown reachability result cannot be decided
    Given reachability "Unknown", effect "<effect>" and guard "<guard>"
    When I decide
    Then the decision is "CannotDecide"

    Examples:
      | effect               | guard            |
      | RuleLowersViolations | GuardMatchesRule |
      | NoMeasurableEffect   | GuardUntested    |

  @D3 @D4 @D5 @D6 @D7 @D8
  Scenario Outline: A loaded rule follows the effect and guard results
    Given reachability "Loaded", effect "<effect>" and guard "<guard>"
    When I decide
    Then the decision is "<decision>"

    Examples:
      | effect               | guard            | decision         | row |
      | Invalid              | GuardUntested    | CannotDecide     | D3  |
      | NotEnoughRuns        | GuardUntested    | NeedsMoreRuns    | D4  |
      | RuleRaisesViolations | GuardUntested    | DeleteCandidate  | D5  |
      | NoMeasurableEffect   | GuardMatchesRule | DeleteCandidate  | D6  |
      | RuleLowersViolations | GuardMatchesRule | ReplaceWithGuard | D7  |
      | RuleLowersViolations | GuardWorse       | Keep             | D8  |
      | RuleLowersViolations | GuardUntested    | Keep             | D8  |

  @D6
  Scenario: The delete-candidate text says "not measurable at this n" and shows the saturated flag
    Given reachability "Loaded", effect "NoMeasurableEffect" and guard "GuardUntested"
    And the saturated flag is true
    When I decide and build the decision text
    Then the decision is "DeleteCandidate"
    And the text says "not measurable at this n"
    And the text shows "saturated: true"

  @D9
  Scenario: The table is total and deterministic
    Given every combination of reachability, effect and guard
    When I decide each combination twice
    Then there are exactly 45 combinations
    And each combination gives one decision value
    And both runs give the same decision

  @D10
  Scenario: ReplaceWithGuard has strict preconditions
    Given every combination of reachability, effect and guard
    When I decide each combination
    Then "ReplaceWithGuard" appears only when reachability is "Loaded" and effect is "RuleLowersViolations" and guard is "GuardMatchesRule"

  @D11
  Scenario: A rule that lowers violations is never a delete candidate
    Given every combination with effect "RuleLowersViolations"
    When I decide each combination
    Then "DeleteCandidate" never appears

  @D12
  Scenario: A masked rule gets no verdict on its content
    Given every combination with reachability "Masked"
    When I decide each combination
    Then the decision is never "Keep", "ReplaceWithGuard" or "DeleteCandidate"

  @E1 @V6
  Scenario Outline: The verdict and the noise status map to an effect result
    Given the noise status "<noise>"
    And the verdict of the LOO arm against the rule arm is "<verdict>"
    When I map it to an effect result
    Then the effect result is "<effect>"

    Examples:
      | noise             | verdict            | effect               |
      | NoiseOk           | InconclusiveSmallN | NotEnoughRuns        |
      | NoiseOk           | FirstHigher        | RuleLowersViolations |
      | NoiseOk           | FirstLower         | RuleRaisesViolations |
      | NoiseOk           | Inconclusive       | NoMeasurableEffect   |
      | NoiseUnmeasured   | InconclusiveSmallN | Invalid              |
      | NoiseUnmeasured   | FirstHigher        | Invalid              |
      | NoiseUnmeasured   | FirstLower         | Invalid              |
      | NoiseUnmeasured   | Inconclusive       | Invalid              |
      | NoiseFloorTooHigh | InconclusiveSmallN | Invalid              |
      | NoiseFloorTooHigh | FirstHigher        | Invalid              |
      | NoiseFloorTooHigh | FirstLower         | Invalid              |
      | NoiseFloorTooHigh | Inconclusive       | Invalid              |

  @E1
  Scenario: The mapping is total over 3 noise statuses and 4 verdicts
    Given every combination of noise status and verdict
    When I map each combination to an effect result
    Then there are exactly 12 combinations
    And only the 4 combinations with "NoiseOk" give an effect other than "Invalid"
