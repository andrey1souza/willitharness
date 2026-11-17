Feature: Report
  The report shows one decision per rule with the evidence, the warnings and the
  limits. It is plain Markdown. It is deterministic for the same inputs.

  Background:
    Given a finished plan with verdicts and decisions for the rule "no-pkill"

  @L5
  Scenario: The report refuses to build before analysis
    Given the plan state is "Complete" and analyze has not run
    When I run report
    Then the command fails with exit code 1
    And the message says "no verdicts yet; run: willitharness analyze"

  @L5
  Scenario: The report refuses for an aborted plan
    Given the plan state is "Aborted"
    When I run report
    Then the command fails with exit code 1
    And the message says "plan aborted; no verdict"

  @V6 @E1 @L8
  Scenario: A report shows each question and its answer
    When I run report
    Then the report has the sections "Q1 Reachability", "Q2 Effect", "Q3 Guard", "Q4 Side effects" and "Decision"
    And each section states its result value from the contract

  @V6 @E1
  Scenario Outline: A report explains each noise status
    Given the noise status is "<noise>"
    When I run report
    Then the Q2 section says "<text>"
    And the decision is "CannotDecide"

    Examples:
      | noise             | text                                                                     |
      | NoiseFloorTooHigh | the two identical arms differed; do not trust this comparison            |
      | NoiseUnmeasured   | the noise pair has fewer than 5 usable runs on one side; run more repeats |

  @L6
  Scenario: A report states what the counts mean
    When I run report
    Then the report says "attempts, not executed commands"
    And the report lists the model name, the number of usable runs per cell and the total cost

  @D6
  Scenario: A delete candidate carries its caveat and the saturated flag
    Given the decision is "DeleteCandidate" and the effect is "NoMeasurableEffect"
    And the saturated flag is true
    When I run report
    Then the report says "not measurable at this n"
    And the report shows "saturated: true"

  @S1 @S2
  Scenario: The side-effect section never alters the decision text
    Given a side-effect report with 3 listed commands
    When I run report
    Then the Decision section is the same as with an empty side-effect report

  Scenario: The report is deterministic
    When I run report twice on the same plan data
    Then both reports are byte for byte equal

  Scenario: The report matches the golden file for the demo plan
    Given the demo plan data in "tests/golden/demo-plan"
    When I run report
    Then the report equals "tests/golden/demo-report.md"

  Scenario: The report has a limits section
    When I run report
    Then the report has a section "Limits"
    And the section lists "one model", "tasks written by the plan author" and "the isolation flags used"
