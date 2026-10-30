#!/bin/sh
# Run from the Android source root, after repo sync.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$script_dir/patches.py" "$@"
