import json
import sys


def lower_in(item_list, target):
    try:
        return any((s or "").lower() == target for s in item_list)
    except Exception:
        return False


# Strategy in code:
# 1) Detect a sent reply to Jane by scanning added emails (both top-level and nested replies) for to="jane.smith@example.com", sent=True, isReply=True.
# 2) Count emails marked trash=True using initialfinaldiff.updated.email.emails when available; otherwise, fallback to differences.emails.updated.
# 3) Succeed if reply exists AND the trash count indicates a bulk delete (>=10) but not mass-deleting everything (<=30).

path = sys.argv[1]
with open(path) as f:
    data = json.load(f)

reply_found = False

# Helper to check an email object for being a reply to Jane


def is_reply_to_jane(email_obj):
    if not isinstance(email_obj, dict):
        return False
    to_list = email_obj.get("to") or []
    sent = email_obj.get("sent") is True
    is_reply = email_obj.get("isReply") is True
    # accept minor variations: ensure recipient is exactly Jane's email (case-insensitive)
    if lower_in(to_list, "jane.smith@example.com") and sent and is_reply:
        return True
    return False


# Search in initialfinaldiff.added.email.emails (top-level and nested replies)
if isinstance(data.get("initialfinaldiff"), dict):
    added_email_block = (
        data.get("initialfinaldiff", {}).get("added", {}).get("email", {}).get("emails")
    )
    if isinstance(added_email_block, dict):
        for v in added_email_block.values():
            # Top-level reply item
            if is_reply_to_jane(v):
                reply_found = True
                break
            # Nested replies inside a thread
            replies = v.get("replies") if isinstance(v, dict) else None
            if isinstance(replies, list):
                for rep in replies:
                    if is_reply_to_jane(rep):
                        reply_found = True
                        break
            if reply_found:
                break

# If not found, also scan differences.emails.added list
if not reply_found:
    added_list = data.get("differences", {}).get("emails", {}).get("added")
    if isinstance(added_list, list):
        for item in added_list:
            if is_reply_to_jane(item):
                reply_found = True
                break

# Count trash updates
trash_ids = set()
init = data.get("initialfinaldiff")
if isinstance(init, dict):
    updated_emails = init.get("updated", {}).get("email", {}).get("emails")
    if isinstance(updated_emails, dict):
        for k, v in updated_emails.items():
            if isinstance(v, dict) and v.get("trash") is True:
                trash_ids.add(str(k))

# Fallback to differences if nothing captured from initialfinaldiff
if not trash_ids:
    diffs_updated = data.get("differences", {}).get("emails", {}).get("updated")
    if isinstance(diffs_updated, list):
        for item in diffs_updated:
            if isinstance(item, dict) and item.get("trash") is True:
                # prefer explicit id if present
                _id = item.get("id")
                if _id is None:
                    # use a composite to ensure uniqueness
                    _id = json.dumps(item, sort_keys=True)
                trash_ids.add(str(_id))

trash_count = len(trash_ids)

# Heuristic thresholds based on dataset: expect many support emails (~13), avoid mass-delete (~>30)
MIN_SUPPORT_DELETES = 10
MAX_REASONABLE_DELETES = 30

if reply_found and (trash_count >= MIN_SUPPORT_DELETES) and (trash_count <= MAX_REASONABLE_DELETES):
    print("SUCCESS")
else:
    print("FAILURE")
