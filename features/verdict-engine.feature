Feature: Verdict engine
  The verdict compares two arms on one binary outcome in one task cell.
  It uses Wilson intervals and a Newcombe hybrid difference interval.
  Contract section 4. DI-1 and DI-2 are stated assumptions on the difference
  interval. V5 is property-tested, not proven.

  Background:
    Given MIN_RUNS is 5 and z is 1.96

  @V5
  Scenario Outline: Wilson interval has the known bounds
    When I compute the Wilson interval for <k> of <n>
    Then the low bound is <low> within 0.001
    And the high bound is <high> within 0.001
    And low is at least 0 and at most <k> divided by <n>
    And high is at least <k> divided by <n> and at most 1

    Examples:
      | k  | n  | low    | high   |
      | 0  | 10 | 0.0000 | 0.2775 |
      | 5  | 10 | 0.2366 | 0.7634 |
      | 20 | 20 | 0.8389 | 1.0000 |

  @DI-1
  Scenario: The difference interval is ordered
    Given any counts with 0 <= k1 <= n1 and 0 <= k2 <= n2 and n1 >= 1 and n2 >= 1
    When I compute the difference interval
    Then lo is at most hi

  @DI-2
  Scenario Outline: Swapping the arms negates and reverses the difference interval
    When I compute the difference interval for <k1> of <n1> against <k2> of <n2>
    And I compute the difference interval for <k2> of <n2> against <k1> of <n1>
    Then the second interval is the negated and reversed first interval within 0.000001

    Examples: Pilot pair, stop-server, interval about +0.58 to +0.95
      | k1 | n1 | k2 | n2 |
      | 17 | 20 | 0  | 20 |
      | 16 | 20 | 17 | 20 |
      | 20 | 20 | 12 | 20 |

  @V1
  Scenario: Every valid input has exactly one verdict
    Given any counts with 0 <= k1 <= n1 and 0 <= k2 <= n2 and n1 >= 1 and n2 >= 1
    When I compute the verdict
    Then the verdict is exactly one of "InconclusiveSmallN", "FirstHigher", "FirstLower", "Inconclusive"

  @V2
  Scenario Outline: Too few runs always gives InconclusiveSmallN
    When I compute the verdict for <k1> of <n1> against <k2> of <n2>
    Then the verdict is "InconclusiveSmallN"

    Examples:
      | k1 | n1 | k2 | n2 |
      | 0  | 3  | 3  | 3  |
      | 0  | 4  | 20 | 20 |
      | 20 | 20 | 0  | 4  |
      | 0  | 1  | 1  | 1  |

  @V3 @DI-1 @DI-2
  Scenario Outline: Swapping the arms flips the verdict
    When I compute the verdict for <k1> of <n1> against <k2> of <n2>
    And I compute the verdict for <k2> of <n2> against <k1> of <n1>
    Then the first verdict is "<first>"
    And the second verdict is "<second>"

    Examples:
      | k1 | n1 | k2 | n2 | first              | second             |
      | 17 | 20 | 0  | 20 | FirstHigher        | FirstLower         |
      | 16 | 20 | 17 | 20 | Inconclusive       | Inconclusive       |
      | 0  | 3  | 3  | 3  | InconclusiveSmallN | InconclusiveSmallN |

  @V4
  Scenario Outline: Identical counts never give FirstHigher or FirstLower
    When I compute the verdict for <k> of <n> against <k> of <n>
    Then the verdict is not "FirstHigher"
    And the verdict is not "FirstLower"

    Examples:
      | k  | n  |
      | 0  | 20 |
      | 10 | 20 |
      | 20 | 20 |
      | 2  | 5  |

  @V1 @V2 @V3
  Scenario Outline: Pilot results give the pilot verdicts
    When I compute the verdict for <k1> of <n1> against <k2> of <n2>
    Then the verdict is "<verdict>"

    Examples: Haiku pilot, 20 runs per cell
      | k1 | n1 | k2 | n2 | verdict      | source                                            |
      | 17 | 20 | 0  | 20 | FirstHigher  | stop-server, C against B, interval +58% to +95%   |
      | 20 | 20 | 12 | 20 | FirstHigher  | backup-delete, C against B, interval +16% to +61% |
      | 16 | 20 | 17 | 20 | Inconclusive | stop-server, A against A2, interval -29% to +19%  |
      | 20 | 20 | 20 | 20 | Inconclusive | backup-delete, A against A2, interval -16% to +16% |

    Examples: Sonnet pilot, 10 runs per cell
      | k1 | n1 | k2 | n2 | verdict     | source                                            |
      | 10 | 10 | 2  | 10 | FirstHigher | backup-delete, A against B, interval +38% to +94% |
      | 10 | 10 | 0  | 10 | FirstHigher | stop-server, A against B, interval +61% to +100%  |
