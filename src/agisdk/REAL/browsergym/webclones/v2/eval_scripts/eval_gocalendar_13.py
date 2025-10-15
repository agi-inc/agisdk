import json, sys

# Verification script for: "Remind me tomorrow to pick up my clothes in Fremont at 11 am."
# Strategy:
# 1) Find an added event whose title implies picking up clothes, with location Fremont, at 11:00.
# 2) Infer "tomorrow" by extracting a YYYY-MM-DD from the file path and checking the event date equals that + 1 day.
#    If no reference date can be extracted, fail conservatively to avoid false positives.


def find_date_in_path(path):
    # Find first occurrence of YYYY-MM-DD without using regex
    for i in range(0, max(0, len(path) - 9)):
        seg = path[i:i+10]
        if (
            len(seg) == 10 and
            seg[0:4].isdigit() and seg[4] == '-' and
            seg[5:7].isdigit() and seg[7] == '-' and
            seg[8:10].isdigit()
        ):
            y = int(seg[0:4])
            m = int(seg[5:7])
            d = int(seg[8:10])
            # rudimentary sanity checks
            if 1 <= m <= 12 and 1 <= d <= 31:
                return y, m, d
    return None


def is_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def add_one_day(y, m, d):
    month_days = [31, 29 if is_leap(y) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    d += 1
    if d > month_days[m-1]:
        d = 1
        m += 1
        if m > 12:
            m = 1
            y += 1
    return y, m, d


def parse_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_added_events(data):
    try:
        added = data.get('differences', {}).get('events', {}).get('added', {})
        if isinstance(added, dict):
            return list(added.values())
        elif isinstance(added, list):
            return added
    except Exception:
        pass
    return []


def safe_lower(s):
    return s.lower() if isinstance(s, str) else ''


def extract_date_time(iso_str):
    # Expect format YYYY-MM-DDTHH:MM:SS...; return (yyyy, mm, dd, hh, mm)
    if not isinstance(iso_str, str):
        return None
    if 'T' not in iso_str:
        return None
    date_part, time_part = iso_str.split('T', 1)
    if len(date_part) != 10:
        return None
    try:
        y = int(date_part[0:4])
        m = int(date_part[5:7])
        d = int(date_part[8:10])
        hh = int(time_part[0:2])
        mm = int(time_part[3:5])
        return (y, m, d, hh, mm)
    except Exception:
        return None


def matches_intent(evt):
    title = safe_lower(evt.get('title', ''))
    loc = safe_lower(evt.get('location', ''))
    start = evt.get('start')
    dt = extract_date_time(start)

    # Must mention pick and clothes
    if not ('pick' in title and 'clothes' in title):
        return False
    # Must include Fremont as location
    if 'fremont' not in loc:
        return False
    # Must be time-based and scheduled at 11:00
    if not dt:
        return False
    y, m, d, hh, mm = dt
    if not (hh == 11 and mm == 0):
        return False
    # allDay should be false if present
    if 'allDay' in evt and evt.get('allDay') is True:
        return False
    return True


def main():
    path = sys.argv[1]
    data = parse_json(path)
    events = get_added_events(data)
    if not events:
        print("FAILURE")
        return

    # Identify candidate events fulfilling the core intent
    candidates = [e for e in events if matches_intent(e)]
    if not candidates:
        print("FAILURE")
        return

    # Infer today's date from the path and require event date == today + 1 day
    ref = find_date_in_path(path)
    if not ref:
        # Cannot verify the 'tomorrow' requirement reliably; fail conservatively
        print("FAILURE")
        return

    ry, rm, rd = ref
    ty, tm, td = add_one_day(ry, rm, rd)

    # Check if any candidate is scheduled for the inferred tomorrow
    for e in candidates:
        dt = extract_date_time(e.get('start'))
        if not dt:
            continue
        y, m, d, hh, mm = dt
        if (y, m, d) == (ty, tm, td):
            print("SUCCESS")
            return

    print("FAILURE")

if __name__ == '__main__':
    main()
