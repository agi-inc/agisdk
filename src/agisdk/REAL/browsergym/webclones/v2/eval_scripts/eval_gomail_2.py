import json
import sys

# Verification script for: Clear any uber emails and notifications emails
# Strategy:
# 1) Collect trashed email IDs from differences.emails.updated (primary). If absent, fallback to initialfinaldiff.
# 2) Identify target IDs for Uber and notifications. First, try dynamic extraction by scanning any nested objects
#    containing 'from' or 'subject' fields with 'uber' or 'notification'. If none found, fallback to known dataset IDs.
# 3) Success if: at least one Uber email trashed AND all notification emails trashed, and no mass over-deletion beyond target scope.
#    Over-deletion guard: total trashed must not exceed target count + 5.


def deep_collect_ids(obj, pred):
    found = set()
    if isinstance(obj, dict):
        # If this dict itself looks like an email object with identifying fields
        lower_from = None
        lower_subject = None
        if "from" in obj and isinstance(obj["from"], str):
            lower_from = obj["from"].lower()
        if "subject" in obj and isinstance(obj["subject"], str):
            lower_subject = obj["subject"].lower()
        id_val = obj.get("id")
        if (lower_from is not None or lower_subject is not None) and id_val is not None:
            if pred(lower_from, lower_subject):
                found.add(str(id_val))
        # Recurse into values
        for v in obj.values():
            found.update(deep_collect_ids(v, pred))
    elif isinstance(obj, list):
        for v in obj:
            found.update(deep_collect_ids(v, pred))
    return found


def get_trashed_ids(data):
    trashed = set()
    # Primary: differences.emails.updated
    diff = data.get("differences", {}).get("emails", {})
    for entry in diff.get("updated", []) or []:
        # entry might be a dict with id and various flags
        if isinstance(entry, dict) and entry.get("trash") is True:
            if "id" in entry:
                trashed.add(str(entry["id"]))
    if trashed:
        return trashed
    # Fallback: initialfinaldiff.updated.email.emails
    init_upd_emails = data.get("initialfinaldiff", {}) or {}
    if isinstance(init_upd_emails, dict):
        upd = init_upd_emails.get("updated", {}) or {}
        email_section = upd.get("email", {}) or {}
        emails_map = email_section.get("emails", {}) or {}
        if isinstance(emails_map, dict):
            for k, v in emails_map.items():
                if isinstance(v, dict) and v.get("trash") is True:
                    trashed.add(str(k))
    return trashed


def main():
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)

    trashed_ids = get_trashed_ids(data)

    # Dynamic extraction for Uber and Notifications from any available detailed objects
    def is_uber(lower_from, lower_subject):
        s = (lower_from or "") + " " + (lower_subject or "")
        return "uber" in s

    def is_notification(lower_from, lower_subject):
        s = (lower_from or "") + " " + (lower_subject or "")
        return "notification" in s  # matches 'notification' and 'notifications'

    uber_ids = deep_collect_ids(data, is_uber)
    notif_ids = deep_collect_ids(data, is_notification)

    # Fallback to known IDs if dynamic detection found none
    if not uber_ids:
        uber_ids = {"48"}
    if not notif_ids:
        # Known notification senders in this dataset
        notif_ids = {"3", "4", "5", "6", "17", "36", "38", "56"}

    # Evaluate conditions
    # 1) Must have trashed something
    if not trashed_ids:
        print("FAILURE")
        return

    # 2) Uber cleared: at least one Uber email trashed
    uber_cleared = bool(trashed_ids & uber_ids)

    # 3) Notifications cleared: all known/detected notification emails trashed
    notifications_cleared_all = notif_ids.issubset(trashed_ids)

    # 4) Over-deletion guard: avoid clearing far more than target scope
    target_total = len(uber_ids | notif_ids)
    total_trashed = len(trashed_ids)
    over_deleted = total_trashed > (target_total + 5)

    if uber_cleared and notifications_cleared_all and not over_deleted:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
