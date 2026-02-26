#!/usr/bin/env python3
"""
TTL cleanup script for AR Laparoscopy jobs.
Deletes job directories older than 24 hours to manage disk space.
Can be run as a cron job or systemd timer.
"""

import os
import sys
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from app.config import JOBS_DIR

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DEFAULT_TTL_HOURS = 24


def get_job_age(job_dir: Path) -> float:
    """
    Get age of job directory in hours.
    
    Args:
        job_dir: Path to job directory
        
    Returns:
        Age in hours (float)
    """
    # Try to get age from status.json first
    status_file = job_dir / "status.json"
    if status_file.exists():
        try:
            import json
            with open(status_file, 'r') as f:
                status = json.load(f)
            
            # Check for created_at timestamp
            if "created_at" in status:
                created_str = status["created_at"]
                try:
                    # Parse ISO format timestamp
                    created_dt = datetime.fromisoformat(created_str.replace('Z', '+00:00'))
                    age = datetime.now() - created_dt.replace(tzinfo=None)
                    return age.total_seconds() / 3600
                except ValueError:
                    pass
        except Exception:
            pass
    
    # Fallback to directory modification time
    try:
        mtime = job_dir.stat().st_mtime
        age_seconds = time.time() - mtime
        return age_seconds / 3600
    except Exception:
        return 0


def cleanup_old_jobs(ttl_hours: int = DEFAULT_TTL_HOURS, dry_run: bool = False) -> dict:
    """
    Clean up job directories older than TTL.
    
    Args:
        ttl_hours: Time to live in hours
        dry_run: If True, only report what would be deleted
        
    Returns:
        Dictionary with cleanup statistics
    """
    if not JOBS_DIR.exists():
        logger.warning(f"Jobs directory not found: {JOBS_DIR}")
        return {"deleted": 0, "errors": 0, "total_size_mb": 0}
    
    stats = {
        "deleted": 0,
        "errors": 0,
        "total_size_mb": 0,
        "skipped": 0
    }
    
    logger.info(f"Starting cleanup with TTL={ttl_hours} hours (dry_run={dry_run})")
    
    for job_dir in JOBS_DIR.iterdir():
        if not job_dir.is_dir():
            continue
        
        job_id = job_dir.name
        age_hours = get_job_age(job_dir)
        
        if age_hours < ttl_hours:
            stats["skipped"] += 1
            logger.debug(f"Skipping {job_id} (age: {age_hours:.1f}h < {ttl_hours}h)")
            continue
        
        # Calculate directory size
        try:
            size_bytes = sum(f.stat().st_size for f in job_dir.rglob('*') if f.is_file())
            size_mb = size_bytes / (1024 * 1024)
            stats["total_size_mb"] += size_mb
        except Exception as e:
            logger.warning(f"Could not calculate size for {job_id}: {e}")
            size_mb = 0
        
        if dry_run:
            logger.info(f"[DRY RUN] Would delete {job_id} (age: {age_hours:.1f}h, size: {size_mb:.1f}MB)")
            stats["deleted"] += 1
        else:
            try:
                shutil.rmtree(job_dir)
                logger.info(f"Deleted {job_id} (age: {age_hours:.1f}h, size: {size_mb:.1f}MB)")
                stats["deleted"] += 1
            except Exception as e:
                logger.error(f"Failed to delete {job_id}: {e}")
                stats["errors"] += 1
    
    logger.info(f"Cleanup complete: deleted={stats['deleted']}, errors={stats['errors']}, "
                f"total_size={stats['total_size_mb']:.1f}MB, skipped={stats['skipped']}")
    
    return stats


def list_jobs():
    """List all jobs with their age and size."""
    if not JOBS_DIR.exists():
        logger.error(f"Jobs directory not found: {JOBS_DIR}")
        return
    
    print(f"{'Job ID':<20} {'Age (h)':<10} {'Size (MB)':<12} {'Status'}")
    print("-" * 60)
    
    for job_dir in sorted(JOBS_DIR.iterdir()):
        if not job_dir.is_dir():
            continue
        
        job_id = job_dir.name
        age_hours = get_job_age(job_dir)
        
        # Get status
        status = "Unknown"
        status_file = job_dir / "status.json"
        if status_file.exists():
            try:
                import json
                with open(status_file, 'r') as f:
                    data = json.load(f)
                status = data.get("status", "Unknown")
            except Exception:
                pass
        
        # Calculate size
        try:
            size_bytes = sum(f.stat().st_size for f in job_dir.rglob('*') if f.is_file())
            size_mb = size_bytes / (1024 * 1024)
        except Exception:
            size_mb = 0
        
        print(f"{job_id:<20} {age_hours:<10.1f} {size_mb:<12.1f} {status}")


def main():
    parser = argparse.ArgumentParser(description="Cleanup old AR Laparoscopy jobs")
    parser.add_argument("--ttl", type=int, default=DEFAULT_TTL_HOURS,
                       help=f"TTL in hours (default: {DEFAULT_TTL_HOURS})")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be deleted without actually deleting")
    parser.add_argument("--list", action="store_true",
                       help="List all jobs with age and size")
    parser.add_argument("--force", action="store_true",
                       help="Force cleanup without confirmation")
    
    args = parser.parse_args()
    
    if args.list:
        list_jobs()
        return
    
    if not args.force and not args.dry_run:
        print(f"This will delete jobs older than {args.ttl} hours.")
        print("Use --dry-run to preview, --force to skip confirmation.")
        
        # Show current jobs
        list_jobs()
        
        response = input("\nContinue? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    
    stats = cleanup_old_jobs(ttl_hours=args.ttl, dry_run=args.dry_run)
    
    if not args.dry_run and stats["deleted"] > 0:
        print(f"\n✅ Cleanup completed: {stats['deleted']} jobs deleted, "
              f"{stats['total_size_mb']:.1f} MB freed")


if __name__ == "__main__":
    main()
