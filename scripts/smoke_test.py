"""Basic real-account smoke test for keep-agent-mem server logic.

Usage:
  GOOGLE_EMAIL=... GOOGLE_MASTER_TOKEN=... python scripts/smoke_test.py

This script performs a lifecycle against Google Keep:
- create note
- get note
- update note
- find note

It is intended for manual verification, not CI.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from server import cli


def main() -> None:
    if not os.getenv("GOOGLE_EMAIL") or not os.getenv("GOOGLE_MASTER_TOKEN"):
        raise SystemExit("Set GOOGLE_EMAIL and GOOGLE_MASTER_TOKEN before running smoke test")

    # --- Note lifecycle ---
    print("Creating note...")
    created = json.loads(cli.create(label="keep-agent-mem", title="keep-agent-mem smoke", text="hello"))
    note_id = created["id"]
    print("Created:", note_id)

    print("Getting note...")
    fetched = json.loads(cli.get(note_id))
    assert fetched["id"] == note_id

    print("Updating note...")
    updated = json.loads(cli.update(note_id, title="keep-agent-mem smoke updated", text="world"))
    assert updated["title"] == "keep-agent-mem smoke updated"

    # --- find() ---
    print("Testing find()...")
    results = json.loads(cli.find(query="keep-agent-mem smoke updated"))
    assert isinstance(results, list)

    print("Smoke test finished successfully")


if __name__ == "__main__":
    main()
