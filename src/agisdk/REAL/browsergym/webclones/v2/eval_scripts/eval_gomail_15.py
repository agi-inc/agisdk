# Task: Clear all no reply emails.
# Verification strategy:
# - In this dataset, emails from senders with exact pattern 'noreply@' (no hyphen) correspond to fixed IDs: 3, 14, 34, 40, 50.
# - Success criteria:
#     * Exactly and only these IDs must be moved to Trash (appear in differences.emails.updated with trash == true)
#     * No other email IDs should be trashed
#     * No emails should be archived/removed (differences.emails.deleted should be empty)
# - Otherwise, mark as FAILURE.

import json, sys

def main():
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    emails_diff = (data.get("differences") or {}).get("emails") or {}

    # Collect IDs that were explicitly trashed in updates
    updated = emails_diff.get("updated") or []
    trashed_ids = set()
    for u in updated:
        # Defensive: ensure dict and fields present
        if isinstance(u, dict) and u.get("trash") is True:
            uid = str(u.get("id")) if u.get("id") is not None else None
            if uid:
                trashed_ids.add(uid)

    # Any archived/removed emails indicates wrong action for this task
    deleted = emails_diff.get("deleted") or []
    if isinstance(deleted, list) and len(deleted) > 0:
        print("FAILURE")
        return

    # Required set of exact 'noreply@' senders (without hyphen) per fixed dataset mapping
    required_ids = {"3", "14", "34", "40", "50"}

    # Check that exactly the required IDs are trashed
    if trashed_ids == required_ids:
        print("SUCCESS")
    else:
        # Fail if any missing or extra
        print("FAILURE")

if __name__ == "__main__":
    main()
