#!/usr/bin/env python3
"""
Database cleanup script for Marty.

Run this script periodically to clean up old conversations, messages, and expired rate limits.
Can be run manually or scheduled via cron/systemd timer.

Usage:
    python scripts/cleanup_database.py [--days-old 30] [--keep-messages 5] [--dry-run]
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path so we can import from it
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database import (  # noqa: E402
    cleanup_database,
    close_db,
    get_db_session,
    test_db_connection,
)


async def wait_for_db(attempts: int = 12, delay: float = 5.0) -> bool:
    """Retry until Postgres accepts connections.

    Railway sleeps the idle database and wakes it on first contact, and the
    connections that arrive while it is still starting are refused.
    """
    for attempt in range(1, attempts + 1):
        if await test_db_connection():
            return True
        if attempt < attempts:
            print(f"⏳ Database not ready ({attempt}/{attempts}), retrying in {delay}s")
            await asyncio.sleep(delay)
    return False


async def main():
    parser = argparse.ArgumentParser(description="Clean up old database records")
    parser.add_argument(
        "--days-old",
        type=int,
        default=30,
        help="Delete conversations older than this many days (default: 30)",
    )
    parser.add_argument(
        "--keep-messages",
        type=int,
        default=5,
        help="Keep this many recent messages per conversation (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    print("🧹 Marty Database Cleanup")
    print(f"📅 Cleaning conversations older than {args.days_old} days")
    print(f"💬 Keeping {args.keep_messages} recent messages per conversation")

    if args.dry_run:
        print("🚫 DRY RUN MODE - No data will be deleted")

    try:
        if not await wait_for_db():
            print("\n❌ Cleanup failed: database never became reachable")
            return 1

        async with get_db_session() as db:
            stats = await cleanup_database(
                db,
                conversation_days_old=args.days_old,
                keep_recent_messages=args.keep_messages,
                dry_run=args.dry_run,
            )

            verb = "Would delete" if args.dry_run else "Deleted"
            headline = (
                "\n✅ Dry run completed - nothing was deleted"
                if args.dry_run
                else "\n✅ Cleanup completed successfully!"
            )

            print(headline)
            print(f"🗑️  {verb} {stats['conversations_deleted']} conversations")
            print(f"💬 {verb} {stats['messages_deleted']} messages")
            print(f"⏱️  {verb} {stats['rate_limits_deleted']} expired rate limits")

    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        return 1
    finally:
        # Ensure database connections are properly closed
        await close_db()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
