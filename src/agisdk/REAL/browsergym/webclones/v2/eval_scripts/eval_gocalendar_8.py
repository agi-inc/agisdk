import sys, json

# Strategy inside code:
# - Search for an event whose title includes both 'email' and 'ashley' in any location.
# - Check differences.events.added, initialfinaldiff.added.calendar.myTasks, and recursively search entire JSON.
# - Parse the start timestamp manually to extract year, month, day, and hour (UTC).
# - Use Zeller's congruence (no external libraries) to verify the date is a Monday.
# - Treat "morning" as UTC hours 14..19 inclusive (covering 7am-12pm US local time when stored in UTC).
# - If any event matches all criteria, print SUCCESS; otherwise FAILURE.

def is_monday(y, m, d):
    # Zeller's congruence for Gregorian calendar
    # h = 0: Saturday, 1: Sunday, 2: Monday, ..., 6: Friday
    if m < 3:
        m += 12
        y -= 1
    q = d
    K = y % 100
    J = y // 100
    h = (q + (13 * (m + 1)) // 5 + K + (K // 4) + (J // 4) + 5 * J) % 7
    return h == 2


def parse_iso_basic(ts):
    # Expected like 'YYYY-MM-DDTHH:MM:SS(.sss)?Z' or with timezone offset
    # We only need year, month, day, hour
    try:
        year = int(ts[0:4])
        month = int(ts[5:7])
        day = int(ts[8:10])
        hour = int(ts[11:13])
        return year, month, day, hour
    except Exception:
        return None


def title_matches(title):
    t = (title or "").strip().lower()
    return ("email" in t) and ("ashley" in t)


def check_events(events_dict):
    """Check events in a dictionary for matching criteria"""
    if not isinstance(events_dict, dict) or not events_dict:
        return False
    
    # Morning window in UTC hours approximating US-local morning (7am-12pm local)
    MORNING_UTC_START = 13  # 13:00Z (expanded to include 1pm UTC)
    MORNING_UTC_END = 19    # 19:59Z

    for ev in events_dict.values():
        title = ev.get('title', '')
        if not title_matches(title):
            continue
        # Try start/startTime first, then fall back to createdAt/updatedAt
        start = ev.get('start') or ev.get('startTime') or ev.get('createdAt') or ev.get('updatedAt')
        parsed = parse_iso_basic(start) if isinstance(start, str) else None
        if not parsed:
            continue
        y, m, d, hh = parsed
        if not is_monday(y, m, d):
            continue
        if MORNING_UTC_START <= hh <= MORNING_UTC_END:
            return True
    return False


def search_recursively(obj):
    """Recursively search for events with matching criteria anywhere in the JSON"""
    if isinstance(obj, dict):
        # Check if this dict looks like an event with title
        if 'title' in obj and isinstance(obj.get('title'), str):
            if check_events({'_': obj}):
                return True
        # Recursively search all values
        for value in obj.values():
            if search_recursively(value):
                return True
    elif isinstance(obj, list):
        for item in obj:
            if search_recursively(item):
                return True
    return False


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Check differences.events.added
    diffs = data.get('differences', {})
    events = diffs.get('events', {})
    added_events = events.get('added', {})
    
    if check_events(added_events):
        print("SUCCESS")
        return

    # Check initialfinaldiff.added.calendar.myTasks
    initial_final_diff = data.get('initialfinaldiff', {})
    added = initial_final_diff.get('added', {})
    calendar = added.get('calendar', {})
    my_tasks = calendar.get('myTasks', {})
    
    if check_events(my_tasks):
        print("SUCCESS")
        return

    # Recursively search the entire JSON structure for any matching event
    if search_recursively(data):
        print("SUCCESS")
        return

    print("FAILURE")

if __name__ == '__main__':
    main()
