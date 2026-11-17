Feature: Side-effect report
  Q4: what else changed when the rule was loaded? Loading a rule file changed other
  behavior in the spike (`git -C` in 22 of 60 loaded runs against 1 of 60 masked).
  S1: the report lists commands whose use differs between arms, with counts per arm.
  S2: the side-effect report never changes a decision.

  @S1 @Q4
  Scenario: A command used far more in one arm is listed
    Given arm "B" ran "git -C" in 22 of 60 runs
    And arm "C" ran "git -C" in 1 of 60 runs
    When I build the side-effect report
    Then the report lists "git -C" with the counts "22 of 60" and "1 of 60"
    And the report says "not part of the rule under test"

  @S1 @Q4
  Scenario: No difference gives an explicit message
    Given every command is used at similar rates in both arms
    When I build the side-effect report
    Then the report says "no command differs between arms"

  @S1 @Q4
  Scenario: Turns and cost are shown with their run counts
    Given arm "B" has mean turns 13.3 over 20 usable runs
    And arm "C" has mean turns 10.4 over 20 usable runs
    When I build the side-effect report
    Then the report shows both means with n
    And the report says "no interval computed" if none is computed

  @S1 @Q4
  Scenario: Alternative channels are listed
    Given 4 of 10 runs in arm "D2" used the "Write" tool after a block
    When I build the side-effect report
    Then the report lists the "Write" tool under alternative channels with "4 of 10"

  @S2
  Scenario: Side effects never change the decision
    Given an effect of "RuleLowersViolations" and a guard of "GuardUntested"
    And a side-effect report with 3 listed commands
    When I decide
    Then the decision is "Keep"
    And the decision is the same as with an empty side-effect report

  @S2
  Scenario: The decision function takes no side-effect input
    When I read the signature of the decision function
    Then its parameters are exactly "reach", "effect" and "guard"
