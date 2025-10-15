import json, sys

def get_top_obj(data, key):
    # Search in initialfinaldiff.added/updated then fallback to root
    if not isinstance(data, dict):
        return None
    if 'initialfinaldiff' in data and isinstance(data['initialfinaldiff'], dict):
        idiff = data['initialfinaldiff']
        for section in ('added', 'updated'):
            sec = idiff.get(section)
            if isinstance(sec, dict) and key in sec:
                return sec.get(key)
    # Fallback if structure differs
    return data.get(key)


def is_5pm_str(s):
    if not isinstance(s, str):
        return False
    t = s.strip().lower().replace('.', '')
    # common variants
    if t in ("5:00 pm", "5 pm", "5pm"):
        return True
    # compact variants without spaces/colon
    comp = t.replace(' ', '').replace(':', '')
    if comp in ("500pm", "05pm", "0500pm"):
        return True
    return False


def has_5pm_notification_for_evening_delight(notification_obj):
    if not isinstance(notification_obj, dict):
        return False
    notifs = notification_obj.get('notifications')
    if not notifs:
        return False
    entries = []
    if isinstance(notifs, dict):
        entries = list(notifs.values())
    elif isinstance(notifs, list):
        entries = notifs
    else:
        return False
    for n in entries:
        if not isinstance(n, dict):
            continue
        rname = n.get('restaurantName') or n.get('restaurant') or ''
        time_str = n.get('time')
        if isinstance(rname, str) and rname.strip().lower() == 'evening delight' and is_5pm_str(time_str):
            return True
    return False


def booking_completed_at_5pm(booking_obj):
    if not isinstance(booking_obj, dict):
        return False
    completed = booking_obj.get('bookingCompleted')
    time_str = booking_obj.get('time')
    # Consider success only if explicitly completed and exactly 5pm
    if completed is True and is_5pm_str(time_str):
        return True
    return False


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

    booking_obj = get_top_obj(data, 'booking')
    notification_obj = get_top_obj(data, 'notification')

    success = False
    # First, if a booking at 5pm was completed
    if booking_completed_at_5pm(booking_obj):
        success = True
    # Else, check notification for Evening Delight at 5pm
    elif has_5pm_notification_for_evening_delight(notification_obj):
        success = True

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()