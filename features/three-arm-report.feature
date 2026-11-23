Feature: Report and decide for the three arms
  A plan with arms C (the component), P (its text as a prompt) and N (nothing)
  gets the verdict of contract section 6a in `decide` and `report`. The plan is
  recognized by the arm labels. A plan without all three labels reports as before.

  Scenario: The report shows the trigger rate and the effect when the skill fires
    Given a finished three-arm plan whose arm C is a skill
    When I run report
    Then the trigger rate of arm C is one number
    And the effect when the skill fires is another number

  Scenario: The report shows turns and cost for each arm
    Given a finished three-arm plan
    When I run report
    Then each of arm C, arm P and arm N has a mean cost and a mean number of turns

  Scenario: The report states the smallest change the runs could detect
    Given a finished three-arm plan
    When I run report
    Then arm C against arm P and arm C against arm N each have a smallest detectable drop

  Scenario: An equal result prints remove candidate only with enough runs
    Given arms C, P and N with equal results
    When I run decide
    Then it prints "remove candidate" only when each arm has at least 20 runs

  Scenario: A plan that has not finished is refused
    Given a three-arm plan that is not Analyzed
    When I run decide or report
    Then it exits 1 with a rule and a fix

  Scenario: A plan with a guard arm is refused
    Given a three-arm plan with a guard_only arm
    When I run decide or report
    Then it exits 1 with a rule and a fix

  Scenario: A plan without all three labels is reported as before
    Given a plan with arms B, C and C2
    When I run report
    Then the report has the sections Q1 to Q4 and no three-arm verdict
