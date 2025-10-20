#!/bin/bash
# Entrypoint for Duplicate File Finder container
# Responsible for starting background services (mount) and launching the app.
set -euo pipefail

MOUNT_SCRIPT="/entrypoint.d/mount.sh"
CLEANUP_SCRIPT="/docker/cleanup.sh"

# Run any custom entrypoint scripts
if [ -d /entrypoint.d ]; then
  for f in /entrypoint.d/*; do
    if [ -x "$f" ]; then
      echo "Running $f"
      "$f"
    fi
  done
fi

# Start the main command (passed as CMD)
echo "Starting main command: $*"
# Trap SIGTERM and SIGINT to run cleanup
_term() {
  echo "Cleaning up..."
  if [ -x "$CLEANUP_SCRIPT" ]; then
    "$CLEANUP_SCRIPT"
  fi
  exit 0
}
trap _term SIGTERM SIGINT

exec "$@"
