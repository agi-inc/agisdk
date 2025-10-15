import json, sys
from datetime import datetime, timedelta, timezone, date

# Strategy inside code:
# 1) Confirm an all-day event titled with phrase "out of town" was added on July 17, 2024.
# 2) Confirm schedule was cleared by detecting at least one event on July 17 removed or moved off the day (in events/joinedEvents deleted or updated).
# 3) Ensure no other events were added on July 17 besides the out-of-town block.
# If all conditions hold, print SUCCESS; otherwise, FAILURE.


def parse_dt(s):
    if not s or not isinstance(s, str):
        return None
    try:
        s2 = s.replace('Z', '+00:00')
        return datetime.fromisoformat(s2)
    except Exception:
        return None


def day_bounds(target_date: date):
    start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def overlaps_day(ev: dict, day_start: datetime, day_end: datetime) -> bool:
    if not isinstance(ev, dict):
        return False
    start = parse_dt(ev.get('start'))
    end = parse_dt(ev.get('end'))
    all_day = ev.get('allDay')
    # Treat allDay as occupying the date of its start
    if all_day and start is not None:
        return day_start.date() == start.date()
    # Otherwise use time overlap
    if start and end:
        return (start < day_end) and (end > day_start)
    if start and not end:
        return day_start <= start < day_end
    return False


def event_covers_day_all_day(ev: dict, target_date: date) -> bool:
    if not isinstance(ev, dict):
        return False
    all_day = ev.get('allDay')
    start = parse_dt(ev.get('start'))
    end = parse_dt(ev.get('end'))
    day_start, day_end = day_bounds(target_date)
    if all_day:
        if start is not None:
            return start.date() == target_date
        return False
    # If not flagged all-day, consider as all-day if it fully spans the day window
    if start and end:
        return (start <= day_start and end >= day_end) or (start == day_start and (end - start) >= timedelta(hours=23, minutes=59))
    return False


def text_has_out_of_town(s: str) -> bool:
    if not s or not isinstance(s, str):
        return False
    try:
        import re
        t = s.lower().replace('-', ' ')
        t = re.sub(r'[^a-z0-9 ]+', ' ', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return 'out of town' in t
    except Exception:
        return 'out of town' in s.lower()


def extract_updated_pairs(updated_dict: dict):
    pairs = []
    if not isinstance(updated_dict, dict):
        return pairs
    for _id, val in updated_dict.items():
        old_ev = None
        new_ev = None
        if isinstance(val, dict):
            if 'old' in val and 'new' in val and isinstance(val.get('old'), dict) and isinstance(val.get('new'), dict):
                old_ev = val['old']
                new_ev = val['new']
            else:
                # Attempt piecewise reconstruction
                old_ev_tmp = {}
                new_ev_tmp = {}
                for key in ['start', 'end', 'allDay', 'title', 'description', 'location', 'meetingId', 'hasMeeting']:
                    if key in val and isinstance(val[key], dict):
                        if 'old' in val[key]:
                            old_ev_tmp[key] = val[key]['old']
                        if 'new' in val[key]:
                            new_ev_tmp[key] = val[key]['new']
                if old_ev_tmp or new_ev_tmp:
                    old_ev = old_ev_tmp
                    new_ev = new_ev_tmp
        if old_ev is not None or new_ev is not None:
            pairs.append((old_ev or {}, new_ev or {}))
    return pairs


def any_clearing_changes(diffs: dict, day_start: datetime, day_end: datetime) -> int:
    cleared = 0
    # events.deleted
    events_deleted = (diffs.get('events', {}) or {}).get('deleted', {}) or {}
    for _id, ev in events_deleted.items():
        if isinstance(ev, dict) and overlaps_day(ev, day_start, day_end):
            cleared += 1
    # events.updated (moved off the day)
    ev_updated = (diffs.get('events', {}) or {}).get('updated', {}) or {}
    for old_ev, new_ev in extract_updated_pairs(ev_updated):
        if overlaps_day(old_ev, day_start, day_end) and not overlaps_day(new_ev, day_start, day_end):
            cleared += 1
    # joinedEvents.deleted
    joined_deleted = (diffs.get('joinedEvents', {}) or {}).get('deleted', {}) or {}
    for _id, ev in joined_deleted.items():
        if isinstance(ev, dict) and overlaps_day(ev, day_start, day_end):
            cleared += 1
    # joinedEvents.updated (moved off the day)
    je_updated = (diffs.get('joinedEvents', {}) or {}).get('updated', {}) or {}
    for old_ev, new_ev in extract_updated_pairs(je_updated):
        if overlaps_day(old_ev, day_start, day_end) and not overlaps_day(new_ev, day_start, day_end):
            cleared += 1
    return cleared


def added_events_on_day(diffs: dict, day_start: datetime, day_end: datetime):
    added = []
    events_added = (diffs.get('events', {}) or {}).get('added', {}) or {}
    for _id, ev in events_added.items():
        if isinstance(ev, dict) and overlaps_day(ev, day_start, day_end):
            added.append(ev)
    joined_added = (diffs.get('joinedEvents', {}) or {}).get('added', {}) or {}
    for _id, ev in joined_added.items():
        if isinstance(ev, dict) and overlaps_day(ev, day_start, day_end):
            added.append(ev)
    return added


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diffs = data.get('differences', {}) or {}

    target_date = date(2024, 7, 17)
    day_start, day_end = day_bounds(target_date)

    # Check out-of-town all-day event added
    oot_added = []
    for _id, ev in ((diffs.get('events', {}) or {}).get('added', {}) or {}).items():
        if not isinstance(ev, dict):
            continue
        title = ev.get('title') or ''
        desc = ev.get('description') or ''
        combined = f"{title} {desc}"
        if event_covers_day_all_day(ev, target_date) and text_has_out_of_town(combined):
            oot_added.append(ev)
    oot_present = len(oot_added) > 0

    # Ensure no other events added on that day (excluding the Out of Town block)
    added_on_day = added_events_on_day(diffs, day_start, day_end)
    non_oot_added_on_day = []
    for ev in added_on_day:
        title = ev.get('title') or ''
        desc = ev.get('description') or ''
        combined = f"{title} {desc}"
        if not (event_covers_day_all_day(ev, target_date) and text_has_out_of_town(combined)):
            non_oot_added_on_day.append(ev)

    # Check that schedule was cleared (some event on that day was removed or moved away)
    cleared_count = any_clearing_changes(diffs, day_start, day_end)

    if oot_present and cleared_count >= 1 and len(non_oot_added_on_day) == 0:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == '__main__':
    main()