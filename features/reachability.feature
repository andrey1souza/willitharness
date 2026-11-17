Feature: Reachability probe
  Q1: is the rule text in the agent's context, in the real directory?
  The probe asks the model for a token. Each arm has a target token (only in the
  rule arm) and a control token (nowhere). Rules P1 to P4, contract section 5.

  Background:
    Given MIN_PROBE_RUNS is 3
    And a target token "ZQ-8841-lumen" planted in the rule file of the rule arm
    And a control token "purple-giraffe-91" planted nowhere

  @P1
  Scenario Outline: Fewer than MIN_PROBE_RUNS usable runs per arm give Unknown
    Given a probe with <usable> usable runs on the rule arm
    When I classify the probe
    Then reachability is "Unknown"

    Examples:
      | usable |
      | 0      |
      | 1      |
      | 2      |

  @P1
  Scenario: The command refuses a run count below MIN_PROBE_RUNS
    When I run the probe command with 2 runs
    Then the command fails with exit code 2
    And the message says "at least 3 probe runs per arm are needed; use --runs 3 or more"

  @P1
  Scenario: Unusable probe runs do not count
    Given a probe with 3 runs where 1 run is unusable
    When I classify the probe
    Then reachability is "Unknown"

  @P2
  Scenario: A control token that appears makes the probe invalid
    Given a probe where the control token appears in 1 of 3 runs
    And the target token appears in 3 of 3 runs
    When I classify the probe
    Then reachability is "Unknown"
    And the message says "control token appeared; the probe cannot be trusted"

  @P3 @Q1
  Scenario: The target token in every run gives Loaded
    Given a fake agent that reports the target token in 3 of 3 runs
    When I run the probe
    Then reachability is "Loaded"

  @P3 @Q1
  Scenario: The target token in no run gives Masked
    Given a fake agent that reports the target token in 0 of 3 runs
    When I run the probe
    Then reachability is "Masked"

  @P3 @Q1
  Scenario: The target token in some runs gives Unknown
    Given a fake agent that reports the target token in 2 of 3 runs
    When I run the probe
    Then reachability is "Unknown"

  @P3 @Q1
  Scenario: An ancestor CLAUDE.md hides an AGENTS.md
    Given a fixture "ancestor-masks-agents" with a CLAUDE.md in the parent directory and an AGENTS.md in the child directory
    When I run the probe in the child directory with the fake agent that follows the fallback rule
    Then reachability is "Masked"

  @P3 @Q1 @live
  Scenario: With no CLAUDE.md anywhere, AGENTS.md loads
    Given a fixture "agents-only" with an AGENTS.md and no CLAUDE.md in any parent directory
    When I run the probe in that directory with the real agent
    Then reachability is "Loaded"

  @P4
  Scenario: The LOO arm must still load a non-target token
    Given the LOO arm built by removing the section "Working here as an agent"
    And a non-target token planted in another section of the harness
    When I probe the LOO arm for the non-target token
    Then the non-target token is "Loaded"
    And the LOO arm is valid

  @P4 @E1
  Scenario: A LOO arm that does not load the non-target token is invalid
    Given the LOO arm probe result for the non-target token is "Masked"
    When I analyze the plan
    Then the LOO arm is invalid
    And the effect result is "Invalid"
    And no effect verdict is emitted
    And the message says "LOO arm does not load its other rules; the effect cannot be reported"

  @L7
  Scenario: An arm with Unknown reachability gets no effect verdict
    Given the rule arm has reachability "Unknown"
    When I analyze the plan
    Then no effect verdict is emitted
    And the decision is "CannotDecide"
