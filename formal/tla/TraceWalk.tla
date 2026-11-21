---- MODULE TraceWalk ----
EXTENDS WillItHarness, Sequences, TLC

CONSTANT WalkDepth
ASSUME WalkDepth \in Nat \ {0}

VARIABLES act, trail

Quote(s) == "\"" \o s \o "\""
Flag(b) == IF b THEN "true" ELSE "false"
CellName(c) == c[1] \o "/" \o c[2]

RECURSIVE ArgList(_)
ArgList(args) == IF args = <<>> THEN "" ELSE "," \o ToString(Head(args)) \o ArgList(Tail(args))
Act(name, args) == "[" \o Quote(name) \o ArgList(args) \o "]"

RECURSIVE JoinNames(_)
JoinNames(names) == IF names = {} THEN ""
                    ELSE LET n == CHOOSE x \in names : TRUE
                         IN Quote(n) \o (IF names \ {n} = {} THEN "" ELSE "," \o JoinNames(names \ {n}))

CellRow(c) == Quote(CellName(c)) \o ":[" \o ToString(started[c]) \o "," \o ToString(usable[c]) \o ","
              \o ToString(unusable[c]) \o "," \o ToString(cost[c]) \o "]"

RECURSIVE JoinCells(_)
JoinCells(cs) == IF cs = {} THEN ""
                 ELSE LET c == CHOOSE x \in cs : TRUE
                      IN CellRow(c) \o (IF cs \ {c} = {} THEN "" ELSE "," \o JoinCells(cs \ {c}))

RECURSIVE JoinReach(_)
JoinReach(arms) == IF arms = {} THEN ""
                   ELSE LET a == CHOOSE x \in arms : TRUE
                        IN Quote(a) \o ":" \o Quote(reach[a]) \o (IF arms \ {a} = {} THEN "" ELSE "," \o JoinReach(arms \ {a}))

Startable == {CellName(c) : c \in {x \in Cells : ENABLED Start(x)}}

RECURSIVE JoinLines(_)
JoinLines(lines) == IF lines = <<>> THEN ""
                    ELSE Head(lines) \o IF Tail(lines) = <<>> THEN "" ELSE "," \o JoinLines(Tail(lines))

StateLine == "{\"act\":" \o act
             \o ",\"state\":" \o Quote(planState)
             \o ",\"worldOk\":" \o Flag(worldOk)
             \o ",\"budget\":" \o ToString(budget)
             \o ",\"arms\":[" \o JoinNames(planArms) \o "]"
             \o ",\"reach\":{" \o JoinReach(Arms) \o "}"
             \o ",\"cells\":{" \o JoinCells(PlanCells) \o "}"
             \o ",\"startable\":[" \o JoinNames(Startable) \o "]"
             \o ",\"analyzable\":" \o Flag(ENABLED Analyze)
             \o ",\"finishable\":" \o Flag(ENABLED FinishComplete \/ ENABLED FinishBudgetStopped)
             \o "}"

Step(label, action) == action /\ act' = label /\ trail' = Append(trail, StateLine)

WalkInit == Init /\ act = Act("Init", <<>>) /\ trail = <<>>

WalkNext ==
    \/ Step(Act("ValidateWorld", <<>>), ValidateWorld)
    \/ Step(Act("WorldChanged", <<>>), WorldChanged)
    \/ \E a \in Arms : Step(Act("CheckReach", <<a>>), CheckReach(a))
    \/ Step(Act("EnterReachChecked", <<>>), EnterReachChecked)
    \/ Step(Act("BeginRunning", <<>>), BeginRunning)
    \/ \E c \in Cells : Step(Act("Start", <<c[1], c[2]>>), Start(c))
    \/ \E c \in Cells, o \in Outcomes, k \in 0..RunCap : Step(Act("Record", <<c[1], c[2], o, k>>), Record(c, o, k))
    \/ \E c \in Cells : Step(Act("Timeout", <<c[1], c[2]>>), Timeout(c))
    \/ Step(Act("FinishComplete", <<>>), FinishComplete)
    \/ Step(Act("FinishBudgetStopped", <<>>), FinishBudgetStopped)
    \/ \E b \in 0..MaxBudget : Step(Act("Resume", <<b>>), Resume(b))
    \/ Step(Act("Analyze", <<>>), Analyze)
    \/ Step(Act("AssessNoise", <<>>), AssessNoise)
    \/ \E x \in Arms : Step(Act("EmitEffect", <<x>>), EmitEffect(x))
    \/ Step(Act("Report", <<>>), Report)
    \/ Step(Act("Abort", <<>>), Abort)
    \/ Step(Act("Terminated", <<>>), Terminated)

Export == Len(trail) = WalkDepth => PrintT("WALK [" \o JoinLines(trail) \o "," \o StateLine \o "]")
====
