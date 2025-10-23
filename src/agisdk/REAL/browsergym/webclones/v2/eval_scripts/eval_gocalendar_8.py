import sys, json

# Strategy inside code:
# - Load differences.events.added and search for an added event whose title includes both 'email' and 'ashley'.
# - Parse the start timestamp manually to extract year, month, day, and hour (UTC).
# - Use Zeller's congruence (no external libraries) to verify the date is a Monday.
# - Treat "morning" as UTC hours 14..19 inclusive (covering 7am-12pm US local time when stored in UTC).
# - If any added event matches all criteria, print SUCCESS; otherwise FAILURE.

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


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diffs = data.get('differences', {})
    events = diffs.get('events', {})
    added = events.get('added', {})

    if not isinstance(added, dict) or not added:
        print("FAILURE")
        return

    # Morning window in UTC hours approximating US-local morning (7am-12pm local)
    MORNING_UTC_START = 14  # 14:00Z
    MORNING_UTC_END = 19    # 19:59Z

    for ev in added.values():
        title = ev.get('title', '')
        if not title_matches(title):
            continue
        start = ev.get('start') or ev.get('startTime')
        parsed = parse_iso_basic(start) if isinstance(start, str) else None
        if not parsed:
            continue
        y, m, d, hh = parsed
        if not is_monday(y, m, d):
            continue
        if MORNING_UTC_START <= hh <= MORNING_UTC_END:
            print("SUCCESS")
            return

    print("FAILURE")

if __name__ == '__main__':
    main()
