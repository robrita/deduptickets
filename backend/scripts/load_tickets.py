#!/usr/bin/env python3
"""
Load sample tickets via POST /api/v1/tickets (full dedup pipeline).

Usage:
    python scripts/load_tickets.py --count 50                    # Load 50 tickets via API
    python scripts/load_tickets.py --ticket-number "#100001"      # Load a single ticket via API
    python scripts/load_tickets.py --batch-file batch.json        # Load tickets listed in a JSON file
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import aiohttp

from config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Path to sample data
DATA_FILE = Path(__file__).parent.parent / "data" / "sample_tickets.json"

# Fields from sample data that are NOT part of TicketCreate (server-generated or internal).
_NON_CREATE_FIELDS = {"id", "pk", "clusterId", "mergedIntoId", "updatedAt", "closedAt"}


def _to_api_payload(ticket: dict) -> dict:
    """Extract TicketCreate-compatible fields from a sample ticket (camelCase)."""
    return {k: v for k, v in ticket.items() if k not in _NON_CREATE_FIELDS and v is not None}


async def load_tickets_via_api(
    tickets_data: list[dict],
    count: int,
    base_url: str,
    api_key: str,
) -> int:
    """
    Load tickets through POST /api/v1/tickets.

    Each ticket goes through the full dedup pipeline: embedding → cluster
    search → multi-signal scoring → three-tier decision → cluster assignment.

    Returns:
        Number of tickets successfully loaded.
    """
    if count > len(tickets_data):
        logger.warning(
            "Requested %d tickets but only %d available. Loading all %d.",
            count,
            len(tickets_data),
            len(tickets_data),
        )
        count = len(tickets_data)

    tickets_to_load = tickets_data[:count]

    # Use proxy endpoint when configured, otherwise default API path
    settings = get_settings()
    if settings.proxy_tickets_endpoint:
        url = settings.proxy_tickets_endpoint
        logger.info("Using proxy endpoint: %s", url)
    else:
        url = f"{base_url}/api/v1/tickets"

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "X-User-ID": "load-ticket-script",
    }

    loaded_count = 0
    skipped_count = 0
    error_count = 0

    async with aiohttp.ClientSession() as session:
        for i, ticket in enumerate(tickets_to_load, 1):
            payload = _to_api_payload(ticket)
            ticket_num = payload.get("ticketNumber", "unknown")

            try:
                async with session.post(url, json=payload, headers=headers) as resp:
                    try:
                        body = await resp.json(content_type=None)
                    except Exception:
                        body = None
                    if resp.status in (200, 201):
                        loaded_count += 1
                        dedup = body.get("dedupDecision", "—") if body else "—"
                        print(f"  [{i}/{count}] {ticket_num} → created (dedup: {dedup})")
                    elif resp.status == 409:
                        skipped_count += 1
                        print(f"  [{i}/{count}] {ticket_num} → already exists, skipped")
                    else:
                        error_count += 1
                        detail = body.get("detail", body) if body else resp.status
                        print(f"  [{i}/{count}] {ticket_num} → ERROR ({resp.status}): {detail}")
            except aiohttp.ClientError as e:
                error_count += 1
                print(f"  [{i}/{count}] {ticket_num} → CONNECTION ERROR: {e}")

    print()
    print(f"  Created: {loaded_count}  Skipped: {skipped_count}  Errors: {error_count}")
    return loaded_count


def _parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Load sample tickets via POST /api/v1/tickets (full dedup pipeline)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/load_tickets.py --count 50                    # Load 50 tickets via API
    python scripts/load_tickets.py --ticket-number "#100001"      # Load a single ticket
    python scripts/load_tickets.py --batch-file tickets.json      # Load from a batch file
        """,
    )
    parser.add_argument(
        "--count",
        type=int,
        help="Number of tickets to load via API (required unless --ticket-number)",
    )
    parser.add_argument(
        "--ticket-number",
        type=str,
        help='Load a single ticket via POST /api/v1/tickets (e.g. "#100001")',
    )
    parser.add_argument(
        "--batch-file",
        type=str,
        help='Path to a JSON file with a list of ticket numbers (e.g. ["#100001", "#100002"])',
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)",
    )

    args = parser.parse_args()

    # Validate arguments — exactly one mode required
    modes = sum(x is not None for x in [args.count, args.ticket_number, args.batch_file])
    if modes == 0:
        parser.error("one of --count, --ticket-number, or --batch-file is required")
    if modes > 1:
        parser.error("--count, --ticket-number, and --batch-file are mutually exclusive")

    return args


def _load_ticket_data(args: argparse.Namespace) -> list[dict]:
    """Load and filter ticket data from sample file based on CLI mode."""
    if not DATA_FILE.exists():
        print(f"ERROR: Sample data file not found: {DATA_FILE}")
        print("Run 'python scripts/generate_sample_tickets.py' first to generate sample data")
        sys.exit(1)

    with DATA_FILE.open(encoding="utf-8") as f:
        tickets_data: list[dict] = json.load(f)

    if args.ticket_number is not None:
        tickets_data = [t for t in tickets_data if t.get("ticketNumber") == args.ticket_number]
        if not tickets_data:
            print(
                f"ERROR: Ticket with ticketNumber '{args.ticket_number}' not found in {DATA_FILE}"
            )
            sys.exit(1)
    elif args.batch_file is not None:
        tickets_data = _filter_batch(tickets_data, args.batch_file)

    return tickets_data


def _filter_batch(tickets_data: list[dict], batch_file: str) -> list[dict]:
    """Filter tickets by a batch file of ticket numbers."""
    batch_path = Path(batch_file)
    if not batch_path.exists():
        print(f"ERROR: Batch file not found: {batch_path}")
        sys.exit(1)
    with batch_path.open(encoding="utf-8") as bf:
        batch_numbers = json.load(bf)
    if not isinstance(batch_numbers, list) or not all(isinstance(n, str) for n in batch_numbers):
        print("ERROR: Batch file must contain a JSON array of ticket number strings")
        sys.exit(1)
    batch_set = set(batch_numbers)
    filtered = [t for t in tickets_data if t.get("ticketNumber") in batch_set]
    missing = batch_set - {t.get("ticketNumber") for t in filtered}
    if missing:
        print(f"WARNING: {len(missing)} ticket(s) not found in sample data: {sorted(missing)}")
    if not filtered:
        print("ERROR: No matching tickets found in sample data")
        sys.exit(1)
    return filtered


async def main() -> None:
    """Main entry point."""
    args = _parse_args()
    settings = get_settings()
    tickets_data = _load_ticket_data(args)
    load_count = args.count if args.count is not None else len(tickets_data)

    print("=" * 60)
    print("Ticket Loader (via API — full dedup pipeline)")
    print("=" * 60)
    print(f"API: {args.base_url}/api/v1/tickets")
    if args.ticket_number is not None:
        print(f"Ticket: {args.ticket_number}")
    elif args.batch_file is not None:
        print(f"Batch file: {args.batch_file}  ({load_count} ticket(s) matched)")
    else:
        print(f"Count: {load_count}")
    print()

    loaded = await load_tickets_via_api(
        tickets_data,
        count=load_count,
        base_url=args.base_url,
        api_key=settings.api_key.get_secret_value(),
    )

    print("=" * 60)
    print(f"Successfully loaded {loaded} ticket(s)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
