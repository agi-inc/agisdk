import sys, json

# Strategy:
# Success if at least one deleted event's title or description contains both 'coffee' and 'sister' (case-insensitive).
# Failure if no events were deleted or none match the keyword conjunction.

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def text_contains_both(text, a, b):
    if not isinstance(text, str):
        return False
    t = text.lower()
    return (a in t) and (b in t)


def event_matches(ev):
    # Check title and description fields for both keywords
    title = ev.get('title')
    desc = ev.get('description')
    combined = ''
    if isinstance(title, str):
        combined += title + ' '
    if isinstance(desc, str):
        combined += desc
    combined = combined.strip().lower()
    if not combined:
        return False
    return ('coffee' in combined) and ('sister' in combined)


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return

    try:
        data = load_json(path)
    except Exception:
        print("FAILURE")
        return

    diffs = data.get('differences') or {}
    events = diffs.get('events') or {}
    deleted = events.get('deleted') or {}

    found = False
    if isinstance(deleted, dict):
        for ev in deleted.values():
            if isinstance(ev, dict) and event_matches(ev):
                found = True
                break

    print("SUCCESS" if found else "FAILURE")

if __name__ == '__main__':
    main()
