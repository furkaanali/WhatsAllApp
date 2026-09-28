#!/bin/bash
set -euo pipefail

# Only run this setup in Claude Code on the web (remote) environments.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

# Install ffmpeg (used by the ffmpeg-usage skill) if it isn't already present.
if ! command -v ffmpeg >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ffmpeg
fi

# Install JS dependencies for the webpack build.
# Best-effort: node-sass (a legacy dependency) can fail its native build on
# newer Python, which shouldn't block the rest of session startup.
cd "$CLAUDE_PROJECT_DIR"
if [ -f yarn.lock ]; then
  yarn install || echo "Warning: yarn install failed (see log above); continuing anyway." >&2
elif [ -f package-lock.json ]; then
  npm install || echo "Warning: npm install failed (see log above); continuing anyway." >&2
else
  npm install || echo "Warning: npm install failed (see log above); continuing anyway." >&2
fi
