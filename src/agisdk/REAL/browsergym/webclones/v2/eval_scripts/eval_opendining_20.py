import json, sys

# Strategy:
# - Success if either a confirmed booking (bookingCompleted True) at exactly 5 PM exists,
#   or a notification is set for Evening Delight at 5 PM.
# - Parse both 'added' and 'updated' sections and normalize time strings for robust matching.

def normalize_time_5pm(s):
    if not s or not isinstance(s, str):
        return False
    t = s.strip().lower().replace('.', '')
    # remove spaces
    t_no_space = t.replace(' ', '')
    # also consider removing colon for variants like '500pm'
    t_no_space_colon = t_no_space.replace(':', '')
    candidates = {
        '5pm', '5:00pm', '05:00pm', '500pm', '0500pm'
    }
    return (t_no_space in candidates) or (t_no_space_colon in candidates)


def get_from_sections(diff_obj, key):
    res = {}
    if isinstance(diff_obj, dict):
        for sec_name in ['added', 'updated']:
            sec = diff_obj.get(sec_name)
            if isinstance(sec, dict):
                sub = sec.get(key)
                if isinstance(sub, dict):
                    # shallow merge top-level fields
                    res.update(sub)
    return res


def any_notification_for_5pm(notification_obj):
    if not isinstance(notification_obj, dict):
        return False
    notifs = notification_obj.get('notifications')

    def check_notif(v):
        if not isinstance(v, dict):
            return False
        rest_name = v.get('restaurantName', '')
        time_str = v.get('time')
        if isinstance(rest_name, str) and 'evening delight' in rest_name.strip().lower():
            if normalize_time_5pm(time_str):
                return True
        return False

    if isinstance(notifs, dict):
        for _, v in notifs.items():
            if check_notif(v):
                return True
    elif isinstance(notifs, list):
        for v in notifs:
            if check_notif(v):
                return True
    return False


def main():
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    diff = data.get('initialfinaldiff', {})

    booking = get_from_sections(diff, 'booking')
    notification = get_from_sections(diff, 'notification')

    booked_5pm = False
    if isinstance(booking, dict):
        time_str = booking.get('time')
        completed = booking.get('bookingCompleted')
        if completed is True and normalize_time_5pm(time_str):
            booked_5pm = True

    notified_5pm = any_notification_for_5pm(notification)

    if booked_5pm or notified_5pm:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == '__main__':
    main()
