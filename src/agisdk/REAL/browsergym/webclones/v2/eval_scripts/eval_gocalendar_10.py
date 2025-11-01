import json, sys

# Verification logic for task:
# "Calendar: My friends just told me they are not free for dinner anymore, cancel that plan on Wednesday"
# Strategy:
# - Success if at least one deleted event exists whose title clearly matches the dinner with friends plan.
# - We detect by checking deleted events' titles for both keywords: "dinner" and "friend" (case-insensitive).
# - Failure if no events deleted or deleted events don't match these keywords.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_success(data):
    diffs = data.get('differences', {})
    events = diffs.get('events', {})
    deleted = events.get('deleted', {})

    if not isinstance(deleted, dict) or len(deleted) == 0:
        return False

    # Check if any deleted event corresponds to the dinner with friends plan
    for _eid, evt in deleted.items():
        if not isinstance(evt, dict):
            continue
        title = evt.get('title')
        if not isinstance(title, str):
            continue
        t = title.strip().lower()
        # Must include both dinner and friend to reduce false positives
        if ('dinner' in t) and ('friend' in t):
            return True

    return False


if __name__ == '__main__':
    try:
        path = sys.argv[1]
        data = load_json(path)
        print('SUCCESS' if is_success(data) else 'FAILURE')
    except Exception:
        # Any error means we couldn't verify; mark as failure.
        print('FAILURE')
