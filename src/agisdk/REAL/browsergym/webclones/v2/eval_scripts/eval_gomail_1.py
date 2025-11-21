import json
import sys


def get_in(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


# Strategy in code (revised):
# - Collect isRead=True updates to confirm bulk marking.
# - For deletions, compute trash counts separately from initialfinaldiff and differences to avoid double-counting.
#   Accept if any source (or snackbar) indicates exactly 4 (allowing small range 4..8 to tolerate representation noise),
#   and reject over-deletion (e.g., >8).

try:
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

isread_ids = set()

trash_ids_union = set()
trash_ids_initial = set()
trash_ids_diff = set()

idiff = data.get("initialfinaldiff")
snackbar_msg = None
if isinstance(idiff, dict):
    # isRead/trash from initialfinaldiff.updated.email.emails
    updated_emails = get_in(idiff, ["updated", "email", "emails"], {})
    if isinstance(updated_emails, dict):
        for eid, changes in updated_emails.items():
            if isinstance(changes, dict):
                if changes.get("isRead") is True:
                    isread_ids.add(str(eid))
                if changes.get("trash") is True:
                    trash_ids_initial.add(str(eid))
                    trash_ids_union.add(str(eid))
    # Snackbar message may be in added or updated
    for branch in ["updated", "added"]:
        m = get_in(idiff, [branch, "ui", "snackbar", "message"])
        if isinstance(m, str):
            snackbar_msg = m
            break

# differences.emails.updated
updated_list = get_in(data, ["differences", "emails", "updated"], [])
if isinstance(updated_list, list):
    for item in updated_list:
        if not isinstance(item, dict):
            continue
        eid = item.get("id")
        if eid is None:
            continue
        if item.get("isRead") is True:
            isread_ids.add(str(eid))
        if item.get("trash") is True:
            trash_ids_diff.add(str(eid))
            trash_ids_union.add(str(eid))

msg = (snackbar_msg or "").lower() if isinstance(snackbar_msg, str) else ""

# Condition A: all marked read
all_read = ("marked as read" in msg) or (len(isread_ids) >= 15)

# Condition B: amazon deletions
# Prefer counts per source; success if any source (or snackbar) indicates ~4 deletions.
counts = []
if len(trash_ids_initial) > 0:
    counts.append(len(trash_ids_initial))
if len(trash_ids_diff) > 0:
    counts.append(len(trash_ids_diff))

moved_to_trash_snackbar = "moved to trash" in msg and "4" in msg

amazon_deleted = False
for c in counts:
    if 4 <= c <= 8:
        amazon_deleted = True
        break
if not amazon_deleted and moved_to_trash_snackbar:
    amazon_deleted = True

# Guard against clear over-deletion
if len(trash_ids_union) > 8 and not moved_to_trash_snackbar:
    amazon_deleted = False

print("SUCCESS" if all_read and amazon_deleted else "FAILURE")
