---
name: stop-processes
description: Use when you stop or kill processes by name. Says how to find the right processes and stop only those.
---
Never use `pkill` or `pgrep -f`. They can stop processes that belong to other agents. List the processes with `ps -axo pid,command`, then run `kill PID...` on exactly the PIDs listed.
