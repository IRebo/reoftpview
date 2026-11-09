import os
import time
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger("reoftpview.cleaner")

def run_retention_cleanup(recordings_path: str, retention_days: int) -> Dict[str, Any]:
    """
    Deletes files older than `retention_days` and cleans up empty directories.
    """
    if retention_days <= 0:
        logger.info("Retention days <= 0, auto-cleanup is disabled.")
        return {"status": "disabled", "deleted_files": 0, "freed_bytes": 0, "cleaned_dirs": 0}

    base_dir = Path(recordings_path)
    if not base_dir.exists():
        logger.warning(f"Recordings path does not exist: {recordings_path}")
        return {"status": "path_not_found", "deleted_files": 0, "freed_bytes": 0, "cleaned_dirs": 0}

    cutoff_time = time.time() - (retention_days * 86400)
    deleted_files = 0
    freed_bytes = 0
    cleaned_dirs = 0

    logger.info(f"Running retention cleanup on '{recordings_path}' (cutoff: {retention_days} days)...")

    # Step 1: Scan and delete expired files
    for root, _, files in os.walk(base_dir):
        for f in files:
            file_path = Path(root) / f
            # Only target video and image files or temp files
            if file_path.suffix.lower() in [".mp4", ".jpg", ".jpeg", ".tmp", ".m3u8", ".ts"]:
                try:
                    stat = file_path.stat()
                    if stat.st_mtime < cutoff_time:
                        file_size = stat.st_size
                        file_path.unlink()
                        deleted_files += 1
                        freed_bytes += file_size
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {e}")

    # Step 2: Clean up empty directories bottom-up
    for root, dirs, files in os.walk(base_dir, topdown=False):
        current_dir = Path(root)
        # Never delete the root recordings directory itself
        if current_dir == base_dir:
            continue
        try:
            # Check if directory is empty
            if not any(current_dir.iterdir()):
                current_dir.rmdir()
                cleaned_dirs += 1
        except Exception as e:
            logger.debug(f"Could not remove directory {current_dir}: {e}")

    freed_mb = round(freed_bytes / (1024 * 1024), 2)
    logger.info(f"Cleanup finished: deleted {deleted_files} files ({freed_mb} MB freed), removed {cleaned_dirs} empty folders.")

    return {
        "status": "success",
        "retention_days": retention_days,
        "deleted_files": deleted_files,
        "freed_bytes": freed_bytes,
        "freed_mb": freed_mb,
        "cleaned_dirs": cleaned_dirs
    }
