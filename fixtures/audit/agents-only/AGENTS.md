# Agent rules

- Run `scripts/check.sh` before every commit.
- Never use `pkill`; list the processes with `ps -axo pid,command`, then run `kill PID`.
- Use `git -C PATH` instead of `cd PATH && git`.
- Never use `git push --force`.
- Always run `make test` before you commit.
- Run `scripts/lint-all.sh` before you push.
- Keep `README.md` short.
- Use `snake_case` for Python names.
- `npm ci && npx tsc --noEmit`
- Never push to `main`. Never force-push it. Push a branch with an explicit refspec: `git push origin BRANCH:refs/heads/BRANCH`.
- Write sentences of 20 words or fewer.
- Name things by what they do, not with comments.
