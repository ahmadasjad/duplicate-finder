# Google Drive FUSE Mounting - Architectural Plan

## Executive Summary

This document outlines implementation of optional FUSE-based Google Drive mounting for the Duplicate File Finder application.
The solution uses rclone to mount Google Drive as a filesystem inside the container, and enables a UI toggle to switch between API mode and mounted mode.

---

## Solution selection: rclone

Why rclone?
- Better maintained and actively developed
- Cross-platform support
- Built-in VFS caching and configuration options
- OAuth support compatible with existing credentials
- Lower memory footprint and better stability than google-drive-ocamlfuse

Alternative considered:
- google-drive-ocamlfuse: less stable, harder to configure in containers

---

## Architecture overview

The mount manager coordinates authentication, rclone configuration, mount/unmount operations, and health checks.
The mounted path is exposed at /mnt/gdrive by default and can be consumed by a local-filesystem provider adapter.

---

## File changes

Add the following files:
- app/storage_providers/google_drive/mount_manager.py
- app/storage_providers/google_drive/rclone_config.py
- docker/entrypoint.sh
- docker/cleanup.sh
- docs/GOOGLE_DRIVE_MOUNT.md

Modify:
- Dockerfile (install rclone and fuse)
- docker-compose.yml (add /dev/fuse, capabilities, mount volume)
- app/config.py (add mount env vars)
- app/storage_providers/google_drive/provider.py (toggle to use mount mode)
- app/ui.py (mount/unmount controls and status)

---

## Dockerfile changes (summary)

- Install fuse and rclone in the image:
```
RUN apt-get update && apt-get install -y fuse rclone && rm -rf /var/lib/apt/lists/*
```
- Create mount directory:
```
RUN mkdir -p /mnt/gdrive
```
- Copy entrypoint and make it executable.

---

## docker-compose changes (summary)

Add to service:
- devices:
  - /dev/fuse
- cap_add:
  - SYS_ADMIN
- security_opt:
  - apparmor:unconfined
- volume for mount:
  - gdrive_mount:/mnt/gdrive:shared

---

## Mount manager — responsibilities

- Generate rclone config from existing credentials (token.json) or prompt user to authenticate if missing.
- Launch rclone mount in background with recommended VFS flags.
- Provide mount, unmount, is_mounted, and health_check APIs.
- Ensure mount only starts after authentication check.
- Expose status for UI and logging.
- Perform graceful unmount on shutdown.

---

## Recommended rclone flags (defaults)

--vfs-cache-mode writes
--vfs-cache-max-size 1G
--vfs-read-chunk-size 128M
--dir-cache-time 5m
--poll-interval 15s
--allow-other           # optional, requires fuse permission
--uid 1000 --gid 1000   # optional: run as application user

---

## Mount workflow (high level)

1. User authenticates via existing OAuth flow (token.json present).
2. UI shows "Mounted Filesystem" option in sidebar after authentication.
3. On user click "Mount", backend calls mount_manager.mount_google_drive().
4. Mount manager writes rclone config and starts rclone as a background process.
5. On success, set st.session_state.gdrive_mounted = True and display mount path.
6. Scan operations can use mounted path via a new LocalAdapter or existing local provider.
7. User may click "Unmount" to stop rclone and clear session state.

---

## Safety and security

- Require authentication before mount; fail fast with a clear message if not authenticated.
- Provide read-only mount option for safety.
- Ensure token.json and credentials.json remain in .gitignore and are not exposed.
- Limit container capabilities to only what is needed for FUSE.

---

## UI changes

- Sidebar access mode radio with "API Mode" and "Mounted Filesystem".
- Mount/Unmount button and mount status indicator.
- Show mount logs and last health check timestamp.

---

## Health checks and monitoring

- is_mounted() uses os.path.ismount or statfs.
- perform a quick read of mount root to ensure responsiveness.
- Optional background thread to re-mount on failure (with backoff).

---

## Cleanup and shutdown

- entrypoint.sh will start application and trap SIGTERM/SIGINT to call cleanup.sh.
- cleanup.sh unmounts /mnt/gdrive using fusermount -u or umount and kills rclone processes.

---

## Documentation

- Create docs/GOOGLE_DRIVE_MOUNT.md with setup steps, prerequisites, and troubleshooting.
- Update README and existing Google Drive setup doc to reference mount mode.

---

## Testing checklist

- Mount attempt before auth should fail.
- Successful mount after auth exposes files under /mnt/gdrive.
- Scans via mounted path should return equivalent metadata to API mode.
- Unmount succeeds and frees mount point.
- Container restart options: auto-mount disabled by default.

---

End of document.
