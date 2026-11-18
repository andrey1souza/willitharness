Feature: Arms and channels in a plan
  An arm records how its rule text reaches the agent: file, skill, hook or
  system_prompt. The default is file. Contract section 2, Channel.

  Background:
    Given a plan with a leave-one-out arm "C"

  @Channel
  Scenario: An arm with no channel defaults to file
    Given a rule arm "B" with no channel
    When I load the plan
    Then the arm "B" has the channel "file"

  @Channel
  Scenario Outline: A known channel is accepted
    Given a rule arm "B" with the channel "<channel>"
    When I load the plan
    Then the arm "B" has the channel "<channel>"

    Examples:
      | channel       |
      | file          |
      | skill         |
      | hook          |
      | system_prompt |

  @Channel
  Scenario: An unknown channel is rejected with the fix
    Given a rule arm "B" with the channel "carrier-pigeon"
    When I load the plan
    Then the plan is rejected
    And the message says "has channel 'carrier-pigeon', which is not one of"
