import sys, json

# Strategy:
# - Parse the final_state_diff.json and scan added events.
# - Success if there exists an added event with:
#   * Title or description mentioning 'basketball' (case-insensitive)
#   * Location includes 'San Francisco' (case-insensitive)
#   * Start time corresponds to 7:00 PM San Francisco time in UTC (02:00Z or 03:00Z)
#   * Not an all-day event
# Otherwise, mark as FAILURE.


def text_has_basketball(*texts):
    for t in texts:
        if isinstance(t, str) and ('basketball' in t.lower()):
            return True
    return False


def location_is_sf(loc):
    if not isinstance(loc, str):
        return False
    l = loc.strip().lower()
    # Accept common variants while avoiding overly broad 'sf' which can be ambiguous
    return 'san francisco' in l


def is_7pm_sf_utc(start_str):
    if not isinstance(start_str, str):
        return False
    s = start_str.strip()
    # Accept common ISO forms with or without milliseconds; check time portion only
    # 7pm in San Francisco is 02:00Z during PDT and 03:00Z during PST
    return ('T02:00' in s) or ('T03:00' in s)


def main():
    if len(sys.argv) < 2:
        print('FAILURE')
        return
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    diffs = data.get('differences') or {}
    events = diffs.get('events') or {}
    added = events.get('added') or {}

    success = False

    if isinstance(added, dict):
        for _id, ev in added.items():
            if not isinstance(ev, dict):
                continue
            title = ev.get('title') or ''
            description = ev.get('description') or ''
            location = ev.get('location') or ''
            start = ev.get('start') or ''
            all_day = ev.get('allDay')

            has_ball = text_has_basketball(title, description)
            loc_ok = location_is_sf(location)
            time_ok = is_7pm_sf_utc(start)
            allday_ok = (all_day is False) or (all_day is None)

            if has_ball and loc_ok and time_ok and allday_ok:
                success = True
                break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
