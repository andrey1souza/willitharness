Feature: Budget, resume, retry, abort and plan lifecycle
  Plan states: Drafted, WorldValidated, ReachabilityChecked, Running, Complete,
  BudgetStopped, Aborted, Analyzed, Reported. Run states: Started, RecordedUsable,
  RecordedUnusable. "Pending" is derived, not stored. Contract section 7.
  Constants: DEFAULT_REPS = 20, MAX_RETRIES = 2. Assumption A-CAP: the runner
  enforces RUN_CAP, so one run never costs more than RUN_CAP.

  Background:
    Given a plan with a fake agent that costs 0.01 per run
    And RUN_CAP is 0.02

  @L1
  Scenario: No run starts before the plan is Running
    Given the plan state is "WorldValidated"
    When I try to start a run
    Then the start is refused
    And no run record exists

  @L1
  Scenario: Reachability must be recorded for every arm of the plan
    Given the world is validated
    And reachability is recorded for 3 of 4 arms
    When I run the plan
    Then the command fails with exit code 1
    And the message names the arm with no reachability result

  @L1
  Scenario: A reachability result of Unknown still counts as recorded
    Given the world is validated
    And reachability is recorded as "Unknown" for every arm
    When I run the plan
    Then the plan state becomes "Running"

  @L2
  Scenario: The budget stops the plan
    Given a budget of 0.05 and 100 planned runs
    When I run the plan
    Then exactly 4 runs start, because a run starts only while spent plus reserved plus 0.02 is at most 0.05
    And the recorded spend is 0.04
    And the plan state is "BudgetStopped"
    And the exit code is 4

  @L2
  Scenario: Parallel runners cannot overspend
    Given a budget of 0.10 and 4 parallel runners
    And reserved is RUN_CAP times the number of started, unrecorded runs
    When I run the plan
    Then spent plus reserved never exceeds 0.10 at any moment
    And the recorded spend at the end is at most 0.10

  @L2
  Scenario: A record replaces the reservation with the real cost
    Given a started run that reserved 0.02
    When the run is recorded with a real cost of 0.01
    Then reserved falls by 0.02
    And spent rises by 0.01

  @L2 @T1
  Scenario: A run whose cost would exceed RUN_CAP is ended and recorded unusable
    Given a run that would cost more than RUN_CAP
    When the runner enforces the cap
    Then the run state is "RecordedUnusable"
    And the recorded cost is at most 0.02

  @L3
  Scenario: A recorded run cannot change
    Given a recorded run "B/stop-server/1"
    When any code tries to write a different record for "B/stop-server/1"
    Then the write fails
    And the stored record is unchanged

  @L3
  Scenario: Counters never decrease
    Given the counters spent, usable runs per cell and attempts per cell
    When any step of the plan runs
    Then no counter is lower than before the step

  @L4
  Scenario: Resume skips full cells
    Given a plan with 20 reps per cell and 12 usable runs recorded in each cell
    When I run the plan again
    Then each cell gets exactly 8 new usable runs
    And no cell has more than 20 usable runs

  @L4
  Scenario: A finished plan resumes to nothing
    Given every cell has 20 usable runs
    When I run the plan again
    Then no run starts
    And the exit code is 0

  @L4
  Scenario: The default number of reps is 20
    Given a plan that sets no reps
    When I load the plan
    Then reps is 20

  @L9
  Scenario: An unusable run does not use a rep, and attempts are capped
    Given a cell with reps 20 where the fake agent fails on every attempt
    And MAX_RETRIES is 2
    When I run the plan
    Then the cell has exactly 22 attempts
    And the cell has 0 usable runs
    And every attempt is "RecordedUnusable" and excluded from n

  @L9
  Scenario: Retries stop when the cell is full
    Given a cell with reps 20 where 2 attempts were unusable and 20 later attempts were usable
    When I run the plan again
    Then no new attempt starts
    And the cell has 22 attempts and 20 usable runs

  @T1
  Scenario: A timed-out run still ends
    Given a run that exceeds the run timeout
    When the timeout fires
    Then the run state is "RecordedUnusable"
    And no run stays in the state "Started"

  @T2
  Scenario: A running plan that is never aborted finishes
    Given a plan in the state "Running" with a fair fake agent and no abort
    When I run the plan to the end
    Then the plan state is "Complete" or "BudgetStopped"

  @T2a
  Scenario: A running plan that may be aborted ends in one of three states
    Given a plan in the state "Running" with a fair fake agent
    And an abort may arrive at any step
    When I run the plan to the end
    Then the plan state is "Complete", "BudgetStopped" or "Aborted"

  @L5
  Scenario: An analyzed plan cannot be aborted
    Given the plan state is "Analyzed"
    When I abort the plan
    Then the command fails with exit code 1
    And the message says "plan already analyzed; abort is not possible"
    And the plan state is "Analyzed"

  @L5 @L2
  Scenario: Abort records every in-flight run as unusable and charges RUN_CAP for it
    Given 3 runs are in flight and the recorded spend is 0.10
    When I abort the plan
    Then the 3 runs are recorded as "RecordedUnusable"
    And the spend is 0.16, because RUN_CAP 0.02 is charged for each
    And the plan state is "Aborted"

  @L5
  Scenario: An aborted plan gets no verdict
    Given the plan state is "Aborted"
    When I run analyze
    Then the command fails with exit code 1
    And the message says "plan aborted; no verdict"

  @L5
  Scenario: No verdict before the plan is Complete or BudgetStopped
    Given the plan state is "Running"
    When I run analyze
    Then the command fails with exit code 1
    And the message says "plan still running; analyze after Complete or BudgetStopped"

  @L5
  Scenario: A BudgetStopped plan can be analyzed
    Given the plan state is "BudgetStopped" with 3 usable runs in a cell
    When I run analyze
    Then the verdict for that cell is "InconclusiveSmallN"

  @L10
  Scenario: A BudgetStopped plan resumes with a higher budget
    Given the plan state is "BudgetStopped" with a budget of 0.05
    And the world hash is unchanged since validation
    And the plan is identical except for budget_usd
    When I resume the plan with a budget of 0.10
    Then the plan state becomes "Running"
    And the reachability results are kept
    And the plan is no longer marked as ended

  @L10
  Scenario: A Complete plan cannot resume
    Given the plan state is "Complete"
    When I resume the plan with a budget of 0.10
    Then the command fails with exit code 1
    And the plan state is "Complete"

  @L10
  Scenario: A BudgetStopped plan with a changed world cannot resume
    Given the plan state is "BudgetStopped"
    And the world hash changed since validation
    When I resume the plan with a higher budget
    Then the command fails with exit code 1
    And the message says the world must be validated again
    And the plan state is "BudgetStopped"

  @L10
  Scenario: A plan that differs from the stored plan in more than the budget cannot resume
    Given the plan state is "BudgetStopped"
    And the plan fingerprint differs from the stored fingerprint
    When I resume the plan with a higher budget
    Then the command fails with exit code 1
    And the plan state is "BudgetStopped"

  @L10
  Scenario: An analyzed plan cannot resume
    Given a BudgetStopped plan that I analyzed
    When I resume the plan with a higher budget
    Then the command fails with exit code 1
    And the plan state is "Analyzed"

  @L10
  Scenario: Analyze on a BudgetStopped plan warns that it ends resume
    Given the plan state is "BudgetStopped"
    When I run analyze
    Then the output warns that analyze ends resume
    And the plan state becomes "Analyzed"

  @L11
  Scenario Outline: A resume with a budget that is not higher is refused
    Given the plan state is "BudgetStopped" with a budget of 0.05
    When I resume the plan with a budget of <new_budget>
    Then the command fails with exit code 1
    And the budget stays 0.05

    Examples:
      | new_budget |
      | 0.05       |
      | 0.04       |

  @L12
  Scenario: A resumed plan is not marked as ended
    Given the plan state is "BudgetStopped" and the plan is marked as ended by the budget
    When I resume the plan with a higher budget
    Then the plan state is "Running"
    And the plan is not marked as ended
