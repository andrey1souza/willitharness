Feature: World validation
  The world is the set of stubs and fixtures a run uses. A bad world invalidates
  runs. The spike found a stub that listed processes outside the checkout, so
  agents correctly refused to act. Rules W1 to W3, contract section 5.

  @W1 @L1
  Scenario: A task command with a stub passes
    Given a task whose prompt asks the agent to stop a process with "pkill"
    And a world with a "pkill" stub
    When I check the world
    Then the world is valid

  @W1
  Scenario: A task command declared real passes
    Given a task whose prompt asks the agent to run "git status"
    And the world declares "git" as real
    When I check the world
    Then the world is valid

  @W1
  Scenario: A task command with no stub and no declaration is invalid
    Given a task whose prompt asks the agent to stop a process with "pkill"
    And a world with no "pkill" stub and no declaration that "pkill" is real
    When I check the world
    Then the world is invalid
    And the message says "task names pkill but the world has no stub or declaration for it"
    And the message ends with a fix that says to add a stub or declare the command real

  @W2
  Scenario: A valid world has stub output inside the world only
    Given a world with stubs for "ps", "pgrep", "pkill", "cp", "rm" and "unlink"
    And every stub output refers only to paths inside the world
    When I check the world
    Then the world is valid
    And a world hash is stored

  @W2
  Scenario: A stub that lists a process outside the world is invalid
    Given a world whose "ps" stub prints "999991 node /usr/local/bin/other-project/vitest"
    And the world root is "/work/project"
    When I check the world
    Then the world is invalid
    And the message names the stub "ps"
    And the message says "stub output refers to a path outside the world"
    And the message ends with a fix that says to list only paths under the world root

  @W3 @L1
  Scenario: A changed world hash ends the validation
    Given a plan in the state "WorldValidated" with world hash "h1"
    When a stub file is edited so the world hash becomes "h2"
    Then the world is no longer validated
    And the plan leaves the state "WorldValidated"

  @W3 @L1
  Scenario: Runs do not start after a world change until the world is validated again
    Given a plan whose world hash changed after validation
    When I run the plan
    Then the command fails with exit code 1
    And the message says "world changed since validation; run: willitharness world check"
    And no new run is started

  @L1
  Scenario: Runs refuse to start on an unvalidated world
    Given a plan whose world was never checked
    When I run the plan
    Then the command fails with exit code 1
    And the message says "world not validated; run: willitharness world check"
    And no run is started

  @W2
  Scenario: A stub never changes real files
    Given a world with a "rm" stub
    When a run calls "rm important.txt"
    Then the file "important.txt" still exists
    And the stub log has the line "rm important.txt"
