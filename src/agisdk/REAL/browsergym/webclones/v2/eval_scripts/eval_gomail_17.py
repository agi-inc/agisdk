import json
import sys

# Strategy:
# - Identify the three emails that belong to the "Today" group (ids '46','47','48') used across this dataset.
# - Consider the task successful if ALL of these emails have been archived or trashed.
# - We detect this by scanning both 'initialfinaldiff' (added/updated -> email.emails) and 'differences' (emails.updated) for archived:true or trash:true flags.
# - Ignore snackbar counts/messages; rely on concrete flags to avoid false positives.


def get_nested(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


try:
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

TODAY_IDS = {"46", "47", "48"}
completed = set()

# Check initialfinaldiff -> added -> email -> emails
if isinstance(data.get("initialfinaldiff"), dict):
    added_emails = get_nested(data, "initialfinaldiff", "added", "email", "emails")
    if isinstance(added_emails, dict):
        for eid, props in added_emails.items():
            if eid in TODAY_IDS and isinstance(props, dict):
                if props.get("archived") is True or props.get("trash") is True:
                    completed.add(eid)

    updated_emails = get_nested(data, "initialfinaldiff", "updated", "email", "emails")
    if isinstance(updated_emails, dict):
        for eid, props in updated_emails.items():
            if eid in TODAY_IDS and isinstance(props, dict):
                if props.get("archived") is True or props.get("trash") is True:
                    completed.add(eid)

# Check differences -> emails -> updated (list of dicts with id and changed flags)
emails_diff = get_nested(data, "differences", "emails")
if isinstance(emails_diff, dict):
    updated_list = emails_diff.get("updated")
    if isinstance(updated_list, list):
        for item in updated_list:
            if not isinstance(item, dict):
                continue
            eid = str(item.get("id")) if item.get("id") is not None else None
            if eid in TODAY_IDS:
                if item.get("archived") is True or item.get("trash") is True:
                    completed.add(eid)

# Final decision: success if all today's emails were archived or trashed
if TODAY_IDS.issubset(completed):
    print("SUCCESS")
else:
    print("FAILURE")
