import json
import sys

# Verification logic:
# - Load final_state_diff.json and look for events in differences.events.added (and updated as fallback)
# - A SUCCESS requires at least one event that:
#   * has title mentioning both "math" and "camp" (case-insensitive)
#   * is marked allDay == True
#   * location contains "sunnyvale" (case-insensitive)
#   * start date is 2024-07-21 and end date is 2024-07-27 (by YYYY-MM-DD from timestamps)
# - Otherwise, print FAILURE


def get_events(data):
    diffs = data.get("differences", {})
    events_block = diffs.get("events", {})
    added = events_block.get("added", {}) or {}
    updated = events_block.get("updated", {}) or {}

    # Combine both added and updated event dicts' values (some tasks may use updated)
    # Only include entries that look like full event objects (have start/end/title fields)
    def valid_event_obj(ev):
        return isinstance(ev, dict) and ("start" in ev or "end" in ev or "title" in ev)

    events = []
    for d in (added, updated):
        if isinstance(d, dict):
            for ev in d.values():
                if valid_event_obj(ev):
                    events.append(ev)
    return events


def date_part(ts):
    if not isinstance(ts, str) or len(ts) < 10:
        return None
    return ts[:10]


def matches_goal(ev):
    title = ev.get("title") or ""
    location = ev.get("location") or ""
    all_day = ev.get("allDay", False)
    start = ev.get("start")
    end = ev.get("end")

    title_l = title.lower()
    location_l = location.lower()

    # Title must reference Math Camp
    if not ("math" in title_l and "camp" in title_l):
        return False

    # Must be all-day
    if all_day is not True:
        return False

    # Location must include Sunnyvale
    if "sunnyvale" not in location_l:
        return False

    # Dates must be 2024-07-21 to 2024-07-27
    sd = date_part(start)
    ed = date_part(end)
    if sd != "2024-07-21" or ed != "2024-07-27":
        return False

    return True


def main():
    try:
        path = sys.argv[1]
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    events = get_events(data)
    for ev in events:
        if matches_goal(ev):
            print("SUCCESS")
            return

    print("FAILURE")


if __name__ == "__main__":
    main()
