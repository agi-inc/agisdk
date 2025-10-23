import sys, json
from datetime import datetime

def parse_iso_dt(s):
    if not isinstance(s, str) or not s:
        return None
    # Ensure 'Z' timezone is handled
    s2 = s.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(s2)
    except Exception:
        return None

def is_wednesday(dt_str):
    dt = parse_iso_dt(dt_str)
    if dt is None:
        return False
    # Monday=0, Wednesday=2
    return dt.weekday() == 2

def collect_deleted_events(data):
    deleted_events = []
    # Primary location: differences.events.deleted
    try:
        del_map = data.get('differences', {}).get('events', {}).get('deleted', {})
        if isinstance(del_map, dict):
            for ev in del_map.values():
                if isinstance(ev, dict):
                    deleted_events.append(ev)
    except Exception:
        pass

    # Secondary location seen in some dumps: initialfinaldiff.added.calendar.deletedEvents
    try:
        init_added_del = (
            data.get('initialfinaldiff', {})
                .get('added', {})
                .get('calendar', {})
                .get('deletedEvents', {})
        )
        if isinstance(init_added_del, dict):
            for ev in init_added_del.values():
                if isinstance(ev, dict):
                    deleted_events.append(ev)
        elif isinstance(init_added_del, list):
            for ev in init_added_del:
                if isinstance(ev, dict):
                    deleted_events.append(ev)
    except Exception:
        pass

    return deleted_events


def main():
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    target_title = 'project sync'

    deleted_events = collect_deleted_events(data)

    success = False
    for ev in deleted_events:
        title = ev.get('title')
        start = ev.get('start')
        if isinstance(title, str) and title.strip().lower() == target_title:
            if is_wednesday(start):
                success = True
                break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    # Strategy: Success requires a deletion of an event titled "Project Sync" whose start date is a Wednesday.
    # We search known deleted-event locations and validate both title match and weekday check.
    main()
