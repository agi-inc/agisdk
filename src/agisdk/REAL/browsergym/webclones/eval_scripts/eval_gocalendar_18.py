import sys, json

# Strategy in code:
# - Load final_state_diff.json and look for newly added events
# - A successful completion requires at least one added event with:
#   * location containing "san ramon" (case-insensitive)
#   * title or description mentioning "tennis" (case-insensitive)
#   * start time exactly at 23:00Z on a Wednesday (UTC) -> corresponds to 4pm in San Ramon during DST
# - We avoid assuming duration or requiring guest/meeting settings; focus on core intent cues


def parse_iso_datetime(dt_str):
    """Parse a subset of ISO8601 'YYYY-MM-DDTHH:MM:SS'Z format and return (y,m,d,h,mi) or None on failure."""
    if not isinstance(dt_str, str) or 'T' not in dt_str:
        return None
    try:
        date_part, time_part = dt_str.split('T', 1)
        y_str, m_str, d_str = date_part.split('-')
        # remove timezone designator for time parsing
        # time_part examples: '23:00:00.000Z' or '23:00:00Z' or with offset; we only need HH:MM
        # Strip trailing 'Z' or timezone offset if present
        tz_pos = max(time_part.find('Z'), time_part.find('+'))
        if tz_pos != -1:
            time_core = time_part[:tz_pos]
        else:
            # if offset like +00:00 exists, handle below
            minus_pos = time_part.find('-')
            if minus_pos > 0:
                time_core = time_part[:minus_pos]
            else:
                time_core = time_part
        # ensure we have at least HH:MM
        hh_str, mi_str = time_core.split(':', 1)[0], time_core.split(':', 1)[1][:2]
        return int(y_str), int(m_str), int(d_str), int(hh_str), int(mi_str)
    except Exception:
        return None


def day_of_week_utc(y, m, d):
    """Sakamoto's algorithm: returns 0=Sunday,1=Monday,...,6=Saturday for Gregorian calendar."""
    t = [0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4]
    y2 = y - 1 if m < 3 else y
    return (y2 + y2//4 - y2//100 + y2//400 + t[m-1] + d) % 7


def is_target_event(ev):
    # Location must include 'san ramon'
    location = ev.get('location') or ''
    if 'san ramon' not in location.lower():
        return False

    # Title or description should mention 'tennis'
    title = (ev.get('title') or '').lower()
    description = (ev.get('description') or '').lower()
    content = title + ' ' + description
    if 'tennis' not in content:
        return False

    # Start time must be Wednesday 23:00Z (interpreting as UTC Wednesday 23:00)
    start = ev.get('start')
    parsed = parse_iso_datetime(start)
    if not parsed:
        return False
    y, m, d, hh, mi = parsed
    # Require exact 23:00
    if not (hh == 23 and mi == 0):
        return False
    dow = day_of_week_utc(y, m, d)  # 0=Sun, 3=Wed
    if dow != 3:
        return False

    return True


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    events_added = []
    try:
        events_added_dict = (
            data.get('differences', {})
                .get('events', {})
                .get('added', {})
        )
        if isinstance(events_added_dict, dict):
            for ev in events_added_dict.values():
                if isinstance(ev, dict):
                    events_added.append(ev)
    except Exception:
        events_added = []

    success = False
    for ev in events_added:
        if is_target_event(ev):
            success = True
            break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()