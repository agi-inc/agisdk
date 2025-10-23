import json, sys

# Verification script for task: Clear all no reply emails
# Strategy:
# - Parse differences.emails.updated to collect ids whose 'trash' was set to true.
# - Succeed only if the trashed ids exactly equal the expected set of no-reply email ids {3,14,34,40,50},
#   ensuring no other emails were trashed. Also fail if UI snackbar indicates 'archived'.


def get_in(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def main():
    fp = sys.argv[1]
    try:
        with open(fp, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    differences = data.get("differences", {})
    emails_diff = differences.get("emails", {})
    updated = emails_diff.get("updated", [])

    trashed_ids = set()
    for item in updated:
        try:
            if item.get("trash") is True:
                # Coerce id to string for consistent comparison
                eid = str(item.get("id"))
                trashed_ids.add(eid)
        except Exception:
            pass

    # If UI snackbar mentions archived, it's a failure for this task
    snackbar_msg = None
    # Look for snackbar in initialfinaldiff.updated.ui.snackbar.message
    snackbar_msg = get_in(data, ["initialfinaldiff", "updated", "ui", "snackbar", "message"]) or snackbar_msg
    if isinstance(snackbar_msg, str) and "archive" in snackbar_msg.lower():
        print("FAILURE")
        return

    # Known target ids for "no reply" emails in this mailbox dataset
    target_ids = {"3", "14", "34", "40", "50"}

    # Success criteria:
    # - Exactly those no-reply emails were moved to Trash (no more, no less)
    if trashed_ids == target_ids and len(trashed_ids) > 0:
        print("SUCCESS")
        return

    # Otherwise, fail
    print("FAILURE")


if __name__ == "__main__":
    main()
