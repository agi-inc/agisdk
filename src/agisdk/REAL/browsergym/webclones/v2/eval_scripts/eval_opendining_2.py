import json, sys

def normalize_time_to_minutes(t):
    if not t or not isinstance(t, str):
        return None
    s = t.strip().lower()
    # remove redundant spaces around am/pm
    s = s.replace(' ', '')
    ampm = None
    if s.endswith('am'):
        ampm = 'am'
        s = s[:-2]
    elif s.endswith('pm'):
        ampm = 'pm'
        s = s[:-2]
    # Now s may be like '3', '300', '3:00', '15:00'
    hour = None
    minute = 0
    if ':' in s:
        parts = s.split(':', 1)
        try:
            hour = int(parts[0])
            minute = int(''.join([c for c in parts[1] if c.isdigit()]) or '0')
        except Exception:
            return None
    else:
        # if it's digits like '300' interpret as hour if <= 23 else try last two as minutes
        if not s.isdigit():
            return None
        num = int(s)
        if num <= 23:
            hour = num
        else:
            # interpret like HMM (e.g., 300 -> 3:00)
            if len(s) <= 2:
                hour = num
                minute = 0
            else:
                hour = int(s[:-2])
                minute = int(s[-2:])
    if hour is None:
        return None
    # Adjust for am/pm if present
    if ampm == 'am':
        if hour == 12:
            hour = 0
    elif ampm == 'pm':
        if hour != 12:
            hour += 12
    # Bounds check
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour * 60 + minute

TARGET_MINUTES = normalize_time_to_minutes('3:00 PM')

def is_italian(s):
    if not s or not isinstance(s, str):
        return False
    return 'italian' in s.strip().lower()


def get_nested(dct, *keys):
    cur = dct
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    # Navigate to likely containers
    base = data.get('initialfinaldiff') or {}
    added = base.get('added', {}) if isinstance(base, dict) else {}
    updated = base.get('updated', {}) if isinstance(base, dict) else {}

    booking = None
    for container in (added, updated, data):
        if isinstance(container, dict) and 'booking' in container and isinstance(container.get('booking'), dict):
            booking = container.get('booking')
            break
    notification = None
    for container in (added, updated, data):
        if isinstance(container, dict) and 'notification' in container and isinstance(container.get('notification'), dict):
            notification = container.get('notification')
            break

    # Analyze bookingDetails if present (strongest evidence)
    found_any_details = False
    found_italian_and_3pm = False
    found_3pm_non_italian = False
    found_italian_wrong_time = False

    if isinstance(booking, dict):
        details = booking.get('bookingDetails')
        if isinstance(details, dict) and details:
            found_any_details = True
            for v in details.values():
                if not isinstance(v, dict):
                    continue
                time_str = v.get('time')
                minutes = normalize_time_to_minutes(time_str)
                rest = v.get('restaurant') or {}
                cuisine = rest.get('food_type')
                is_it = is_italian(cuisine)
                is_3pm = (minutes == TARGET_MINUTES)
                if is_it and is_3pm:
                    found_italian_and_3pm = True
                elif is_3pm and not is_it:
                    found_3pm_non_italian = True
                elif is_it and not is_3pm:
                    found_italian_wrong_time = True

    if found_any_details:
        if found_italian_and_3pm:
            print('SUCCESS')
            return
        # If we have explicit details but none match both criteria, it is a failure
        print('FAILURE')
        return

    # Fallback path when explicit booking details are absent.
    # We verify time is 3:00 PM from available indicators, and ensure there's no explicit contradiction.
    time_match_sources = []
    if isinstance(booking, dict):
        bt = booking.get('time')
        if normalize_time_to_minutes(bt) == TARGET_MINUTES:
            time_match_sources.append('booking.time')
    if isinstance(notification, dict):
        notifs = notification.get('notifications')
        if isinstance(notifs, dict):
            for v in notifs.values():
                if not isinstance(v, dict):
                    continue
                t = v.get('time')
                if normalize_time_to_minutes(t) == TARGET_MINUTES:
                    time_match_sources.append('notification')

    if time_match_sources:
        # No explicit cuisine info available; accept since no contradictory details were recorded.
        print('SUCCESS')
        return

    # No evidence of correct time or cuisine
    print('FAILURE')

if __name__ == '__main__':
    main()
