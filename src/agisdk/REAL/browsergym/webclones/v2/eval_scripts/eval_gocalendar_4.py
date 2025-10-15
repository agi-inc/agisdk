import json, sys

# Strategy:
# 1) Confirm an all-day event titled "Hospital" (case-insensitive) was added.
# 2) Verify that at least one event on that same date was deleted (from personal or joined events), indicating schedule clearing.
# If both conditions are met -> SUCCESS, else -> FAILURE.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_nested(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def values_list(maybe_dict):
    if isinstance(maybe_dict, dict):
        return list(maybe_dict.values())
    return []


def extract_date(iso):
    if not isinstance(iso, str):
        return None
    if 'T' in iso:
        return iso.split('T', 1)[0]
    # Already date-like
    return iso[:10]


def is_hospital_all_day(evt):
    if not isinstance(evt, dict):
        return False
    title = str(evt.get('title', '')).strip().lower()
    all_day = evt.get('allDay', False) is True
    return all_day and ('hospital' in title)


def event_date(evt):
    start = evt.get('start')
    return extract_date(start)


def main():
    path = sys.argv[1]
    data = load_json(path)
    diffs = data.get('differences', {}) if isinstance(data, dict) else {}

    events_added = get_nested(diffs, 'events', 'added') or {}
    joined_added = get_nested(diffs, 'joinedEvents', 'added') or {}
    events_deleted = get_nested(diffs, 'events', 'deleted') or {}
    joined_deleted = get_nested(diffs, 'joinedEvents', 'deleted') or {}

    # Find all added hospital all-day events across personal and joined events
    added_evts = values_list(events_added) + values_list(joined_added)
    hospital_events = [e for e in added_evts if is_hospital_all_day(e) and event_date(e)]

    if not hospital_events:
        print('FAILURE')
        return

    # Build a set of dates on which at least one event was deleted
    deleted_evts = values_list(events_deleted) + values_list(joined_deleted)
    deleted_dates = set()
    for d in deleted_evts:
        dt = event_date(d)
        if dt:
            deleted_dates.add(dt)

    # Success if any hospital all-day event has at least one deletion on the same date
    for hevt in hospital_events:
        hdate = event_date(hevt)
        if hdate and hdate in deleted_dates:
            print('SUCCESS')
            return

    print('FAILURE')

if __name__ == '__main__':
    main()
