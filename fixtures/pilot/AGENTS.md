# Project rules

## Working here as an agent

- Never use `pkill` or `pgrep -f`. They can stop processes that belong to other agents. List the processes with `ps -axo pid,command`, then run `kill PID...` on exactly the PIDs listed.
- Never run bare `cp` or `rm`. They are aliased and ask for confirmation. Use `command cp -f SOURCE TARGET` and `unlink PATH`.
- Use `git -C <worktree>` for git commands. Never run git outside your worktree.

## Style

- Keep answers short.
- Say exactly which commands you ran.

## Testing

- Run the unit tests before you finish a change.
