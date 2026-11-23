Feature: Content against filler
  Arm PL is filler text of the same length as the component text. The verdict
  compares arm C with arm PL, as in contract section 6b. A lower violation rate is
  better. The function is total on 4 x 4 x 4 x 2 = 128 inputs.

  @PB4
  Scenario: A component that beats the filler text has content that helps
    Given arm C has 2 of 20 runs with the violation
    And arm PL has 12 of 20 runs with the violation
    And arm N has 12 of 20 runs with the violation
    When I build the content verdict
    Then the content verdict is "ContentBeatsFiller"

  @PB6
  Scenario: A component equal to the filler text, and both better than nothing, shows that added text helps
    Given arm C has 3 of 20 runs with the violation
    And arm PL has 3 of 20 runs with the violation
    And arm N has 14 of 20 runs with the violation
    When I build the content verdict
    Then the content verdict is "AddedTextHelps"
    And the report says "added text helps and the content does not"

  @PB8
  Scenario: A component equal to the filler text, with only one of them better than nothing, is unclear
    Given arm C has 0 of 20 runs with the violation
    And arm PL has 3 of 20 runs with the violation
    And arm N has 8 of 20 runs with the violation
    When I build the content verdict
    Then the content verdict is "Unclear"

  @PB7
  Scenario: A component equal to the filler text and equal to nothing shows that nothing helps
    Given arm C has 10 of 20 runs with the violation
    And arm PL has 10 of 20 runs with the violation
    And arm N has 10 of 20 runs with the violation
    When I build the content verdict
    Then the content verdict is "NothingHelps"

  @PB5
  Scenario: Filler text that beats the component is reported
    Given arm C has 14 of 20 runs with the violation
    And arm PL has 3 of 20 runs with the violation
    And arm N has 14 of 20 runs with the violation
    When I build the content verdict
    Then the content verdict is "FillerBeatsContent"

  @PB3
  Scenario: Almost no violations in arm N leaves no room to help, as a policy choice
    Given arm C has 0 of 20 runs with the violation
    And arm PL has 10 of 20 runs with the violation
    And arm N has 0 of 20 runs with the violation
    When I build the content verdict
    Then the content verdict is "NoRoomToHelp"
    And the report says "policy choice"
    And the report says "not a measurement"

  @PB2
  Scenario: An arm with too few runs gives no content verdict
    Given arm C has 0 of 3 runs with the violation
    And arm PL has 15 of 20 runs with the violation
    And arm N has 15 of 20 runs with the violation
    When I build the content verdict
    Then the content verdict is "Inconclusive"

  @PB1
  Scenario: The function is total and deterministic
    Given every combination of three verdicts and the clean flag
    When I build the content verdict for each combination twice
    Then there are exactly 128 combinations
    And each combination gives one verdict value
    And both runs give the same verdict
    And every verdict value is reached by some combination

  @PB6
  Scenario: The report shows turns and cost for arm PL
    Given a finished three-arm plan with arm PL
    When I run report
    Then arm PL has a mean cost and a mean number of turns
    And the report has a section that compares arm C with arm PL

  @PB6
  Scenario: Decide prints the content verdict after the three-arm verdict
    Given a finished three-arm plan with arm PL
    When I run decide
    Then it prints one content line for each task

  @PB9
  Scenario: A plan without arm PL is reported as before
    Given a finished three-arm plan without arm PL
    When I run report or decide
    Then there is no section that compares arm C with arm PL
    And decide prints one line for each task
