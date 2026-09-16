#!/bin/bash
# Wrapper so launchd can run the token refresh with a single absolute path.
# Finds its own location so it works regardless of where the repo lives.

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR" || exit 1

source venv/bin/activate
python3 scripts/get_refresh_token.py
