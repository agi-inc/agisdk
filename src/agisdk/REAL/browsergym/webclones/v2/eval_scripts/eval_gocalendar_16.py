import sys, json

def get_nested(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

# Strategy:
# - Task requires canceling (deleting) the "Reading Time" event on Wednesday. In diffs, a successful run shows the event under events.deleted.
# - We generalize: SUCCESS if any deleted event has a title containing "reading" (case-insensitive). Otherwise FAILURE.

try:
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

# Extract deleted events dict safely
deleted_events = get_nested(data, ["differences", "events", "deleted"], default={})

success = False
if isinstance(deleted_events, dict) and deleted_events:
    for ev in deleted_events.values():
        if isinstance(ev, dict):
            title = ev.get("title", "")
            if isinstance(title, str) and "reading" in title.lower():
                success = True
                break

print("SUCCESS" if success else "FAILURE")