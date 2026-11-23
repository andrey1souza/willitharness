Feature: Three-arm verdict
  One verdict from arm C (the real component), arm P (the same text as a plain
  prompt) and arm N (nothing), as in contract section 6a. A lower violation rate is
  better. The function is total on 4 x 4 x 2 = 32 inputs.

  @TA4
  Scenario: A component that beats its own text as a prompt is kept
    Given arm C has 2 of 20 runs with the violation
    And arm P has 12 of 20 runs with the violation
    And arm N has 12 of 20 runs with the violation
    When I build the three-arm verdict
    Then the verdict is "KeepComponent"

  @TA5
  Scenario: A component equal to its prompt and better than nothing is replaced
    Given arm C has 3 of 20 runs with the violation
    And arm P has 3 of 20 runs with the violation
    And arm N has 14 of 20 runs with the violation
    When I build the three-arm verdict
    Then the verdict is "ReplaceWithPrompt"

  @TA6
  Scenario: A component equal to nothing is a delete candidate
    Given arm C has 10 of 20 runs with the violation
    And arm P has 10 of 20 runs with the violation
    And arm N has 10 of 20 runs with the violation
    When I build the three-arm verdict
    Then the verdict is "DeleteCandidate"

  @TA3
  Scenario: Almost no violations in arm N gives insurance, as a policy choice
    Given arm C has 0 of 20 runs with the violation
    And arm P has 10 of 20 runs with the violation
    And arm N has 0 of 20 runs with the violation
    When I build the three-arm verdict
    Then the verdict is "InsuranceKeep"
    And the report says "policy choice"
    And the report says "not a measurement"

  @TA2
  Scenario: An arm with too few runs gives no verdict
    Given arm C has 0 of 3 runs with the violation
    And arm P has 15 of 20 runs with the violation
    And arm N has 15 of 20 runs with the violation
    When I build the three-arm verdict
    Then the verdict is "Inconclusive"

  @TA7
  Scenario Outline: An input the backlog does not name gives Inconclusive
    Given the verdict of arm P against arm C is "<prompt>"
    And the verdict of arm N against arm C is "<nothing>"
    And arm N is not clean
    When I build the three-arm verdict from the two verdicts
    Then the verdict is "Inconclusive"

    Examples:
      | prompt       | nothing      |
      | FirstLower   | FirstHigher  |
      | FirstLower   | FirstLower   |
      | FirstLower   | Inconclusive |
      | Inconclusive | FirstLower   |

  @TA1
  Scenario: The function is total and deterministic
    Given every combination of two verdicts and the clean flag
    When I build the three-arm verdict for each combination twice
    Then there are exactly 32 combinations
    And each combination gives one verdict value
    And both runs give the same verdict
    And every verdict value is reached by some combination
