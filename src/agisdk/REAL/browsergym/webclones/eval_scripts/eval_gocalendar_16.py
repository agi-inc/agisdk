import sys, json
from datetime import datetime

def parse_iso(dt_str):
    if not isinstance(dt_str, str):
        return None
    # Support trailing 'Z'
    s = dt_str.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def get_updated_field(obj, key):
    # updated diffs might be raw values or {old:..., new:...}
    if key not in obj:
        return None
    val = obj.get(key)
    if isinstance(val, dict) and 'new' in val:
        return val.get('new')
    return val

def has_notification(ev):
    # Check for notification presence in common places
    co = ev.get('calendarOptions') or {}
    notif = co.get('notification')
    if isinstance(notif, str) and notif.strip() and notif.strip().lower() not in {'none', 'no notification'}:
        return True
    # Also check possible plural/list
    notifs = co.get('notifications')
    if isinstance(notifs, list) and len(notifs) > 0:
        return True
    # Some schemas may store reminders at top-level
    top_notif = ev.get('notification')
    if isinstance(top_notif, str) and top_notif.strip() and top_notif.strip().lower() not in {'none', 'no notification'}:
        return True
    return False

def title_matches(title):
    if not isinstance(title, str):
        return False
    t = title.lower()
    # Simple word-based match to ensure both words appear
    # Accept variants like "Dinner with Team"
    return ('team' in t) and ('dinner' in t)

def event_matches(ev):
    # Extract fields
    title = ev.get('title')
    start_str = ev.get('start')
    if not start_str and 'start' in ev and isinstance(ev['start'], dict):
        start_str = ev['start'].get('new') or ev['start'].get('value')

    if not (title_matches(title)):
        return False

    dt = parse_iso(start_str)
    if not dt:
        return False

    # Check month/day is October 10 and time is 21:00
    if not (dt.month == 10 and dt.day == 10 and dt.hour == 21 and dt.minute == 0):
        return False

    # Ensure a reminder exists
    if not has_notification(ev):
        return False

    return True

def check(data):
    diffs = data.get('differences') or {}
    events = diffs.get('events') or {}

    # Collect candidate events from added and updated
    candidates = []
    for section in ('added', 'updated'):
        sec = events.get(section) or {}
        if isinstance(sec, dict):
            for _id, ev in sec.items():
                # If updated diff contains nested changes, try to reconstruct minimal ev-like dict
                if section == 'updated' and isinstance(ev, dict):
                    # Try to build a flat representation with potential 'new' fields
                    norm = {}
                    for k, v in ev.items():
                        if isinstance(v, dict) and 'new' in v:
                            norm[k] = v['new']
                        else:
                            norm[k] = v
                    candidates.append(norm)
                else:
                    candidates.append(ev)

    # If no candidates found, immediate failure
    if not candidates:
        return False

    for ev in candidates:
        try:
            if event_matches(ev):
                return True
        except Exception:
            continue
    return False

def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    result = check(data)
    print('SUCCESS' if result else 'FAILURE')

if __name__ == '__main__':
    main()