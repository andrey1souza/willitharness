Feature: Detectors for forbidden and required actions
  A rule's detector decides whether a run broke the rule. Kind forbidden: a command
  or tool call matches. Kind required: a named action is absent before a named point.
  Contract section 5, R1.

  Background:
    Given a required detector for the action "gbrain query" before the first edit

  @R1
  Scenario: A required action before the named point is not a violation
    Given a complete transcript where "gbrain query" is called before the first edit
    When I run the detector
    Then the run did not break the rule

  @R1
  Scenario: A required action missing before the named point is a violation
    Given a complete transcript where the first edit comes with no "gbrain query" before it
    When I run the detector
    Then the run broke the rule

  @R1
  Scenario: A transcript cut off before the named point is unusable
    Given a transcript that ends before any result event
    When I run the detector
    Then the run is unusable for the outcome
    And the run counts in neither n nor k
