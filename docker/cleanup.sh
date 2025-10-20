#!/bin/bash
# Cleanup script to unmount rclone mounts and kill rclone processes.

MOUNT_POINT="${GDRIVE_MOUNT_PATH:-/mnt/gdrive}"
set +e

echo "Running cleanup: attempting to unmount ${MOUNT_POINT}"

# Try fusermount -u, fallback to umount
if command -v fusermount >/dev/null 2>&1; then
  fusermount -u "${MOUNT_POINT}" || true
else
  umount "${MOUNT_POINT}" || true
fi

# Kill any leftover rclone processes
pkill -f "rclone mount" || true

echo "Cleanup complete"
