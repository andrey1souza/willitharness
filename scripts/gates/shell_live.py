import json
import sys
import tempfile
from pathlib import Path

from willitharness import claude_agent
from willitharness.probe import RESULT_EVENT

PROMPT = "Run exactly this bash command and reply with its output only: type cp"
ALLOWED_COMMANDS = ("type",)
BUDGET_USD = 0.03
COST_CAP_USD = 0.05
ALIAS_WORD = "alias"
CLEAN_MARKER = "/bin/cp"
EXIT_PASSED = 0
EXIT_FAILED = 1
NOT_PROVEN_MESSAGE = "shell not clean"


def shell_command(prompt, model, budget):
    assert prompt, "shell_command needs a prompt. Fix: pass the probe prompt."
    assert model and budget > 0, f"shell_command needs a model and a budget above 0, got {model!r} and {budget!r}. Fix: pass both."
    command = claude_agent.build_command(prompt, model, budget, claude_agent.tool_policy(False, ALLOWED_COMMANDS))
    assert "Bash" in command, f"the shell check needs the Bash tool, got {command!r}. Fix: build the command with an effect policy."
    return command


def shell_reply_of(lines):
    assert isinstance(lines, list), f"reply_of needs the transcript lines, got {type(lines).__name__}. Fix: pass the lines."
    reply = ""
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("type") == RESULT_EVENT:
            reply = str(event.get("result", ""))
    assert isinstance(reply, str), f"the reply is {type(reply)}. Fix: read the result field as text."
    return reply


def shell_is_clean(reply):
    assert isinstance(reply, str), f"shell_is_clean needs text, got {type(reply).__name__}. Fix: pass the agent's reply."
    verdict = ALIAS_WORD not in reply.lower() and CLEAN_MARKER in reply
    assert verdict in (True, False), f"the verdict is {verdict!r}, not a bool"
    return verdict


def main(runner):
    assert callable(runner), f"runner must be a function that runs the agent, got {runner!r}. Fix: pass one."
    assert COST_CAP_USD > BUDGET_USD, f"the cost cap {COST_CAP_USD} must exceed the run budget {BUDGET_USD}. Rule: a run cannot be over the cap by design. Fix: set COST_CAP_USD above BUDGET_USD."
    with tempfile.TemporaryDirectory(prefix="willitharness-shell-") as directory:
        lines = runner(Path(directory), shell_command(PROMPT, claude_agent.DEFAULT_MODEL, BUDGET_USD))
    reply = shell_reply_of(lines)
    cost = claude_agent.transcript_cost(lines)
    print(f"reply: {reply!r}")
    print(f"cost: ${cost:.4f}")
    if not shell_is_clean(reply) or cost > COST_CAP_USD:
        print(NOT_PROVEN_MESSAGE)
        return EXIT_FAILED
    print("GATE SHELL PASS")
    return EXIT_PASSED


def shell_agent_runner(directory, command):
    assert directory.is_dir(), f"{directory} is not a directory. Fix: pass the working folder."
    assert command, "the live runner needs a command. Fix: pass the claude command."
    return claude_agent.run_command(directory, command)


if __name__ == "__main__":
    sys.exit(main(shell_agent_runner))
