#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
exec uv run python scripts/gates/guard_repro.py "$@"
