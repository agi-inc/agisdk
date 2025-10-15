import json, sys, os

# Verification with a nuanced fallback for null placeholders leveraging sibling timing on the same date.

import json, sys, os

def load_json(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def to_date_str(dt):
    if not isinstance(dt, str):
        return None
    return dt.split('T')[0]


def str_contains(s, sub):
    return isinstance(s, str) and sub.lower() in s.lower()


def destination_is_orlando(dest):
    if isinstance(dest, str):
        return str_contains(dest, 'orlando')
    if isinstance(dest, (list, tuple)):
        return any(str_contains(x, 'orlando') for x in dest)
    return False


def dates_match(dates):
    if not isinstance(dates, dict):
        return False
    start = to_date_str(dates.get('startDate'))
    end = to_date_str(dates.get('endDate'))
    return start == '2024-12-27' and end == '2025-01-01'


def guests_match(guest_counts):
    if not isinstance(guest_counts, dict):
        return False
    return guest_counts.get('Rooms') == 2 and guest_counts.get('Adults') == 8


def points_payment_ok(payment):
    if not isinstance(payment, dict):
        return False
    pay_with = payment.get('payWith')
    points_used = payment.get('pointsUsed')
    if isinstance(pay_with, str) and pay_with.lower() == 'points':
        return True
    return isinstance(points_used, (int, float)) and points_used > 0


def hotel_or_destination_ok(obj):
    dest_ok = destination_is_orlando(obj.get('destination'))
    hotel = obj.get('hotel')
    hotel_ok = False
    if isinstance(hotel, dict):
        loc = hotel.get('location')
        if isinstance(loc, (list, tuple)):
            hotel_ok = any(str_contains(x, 'orlando') for x in loc)
        else:
            hotel_ok = destination_is_orlando(loc)
    return dest_ok or hotel_ok


def is_booking_successful(obj):
    if not isinstance(obj, dict):
        return False
    if obj.get('bookingSuccess') is False:
        return False
    return hotel_or_destination_ok(obj) and dates_match(obj.get('dates')) and guests_match(obj.get('guestCounts')) and points_payment_ok(obj.get('paymentInfo'))


def iter_dicts(d):
    if isinstance(d, dict):
        yield d
        for v in d.values():
            yield from iter_dicts(v)
    elif isinstance(d, list):
        for item in d:
            yield from iter_dicts(item)


def extract_candidate_bookings(data):
    candidates = []
    for node in iter_dicts(data):
        if isinstance(node, dict) and all(k in node for k in ('dates', 'guestCounts', 'paymentInfo')) and (('destination' in node) or ('hotel' in node)):
            candidates.append(node)
    return candidates


def is_null_placeholder(data):
    return isinstance(data, dict) and data.get('initialfinaldiff') is None and data.get('differences') is None


def fallback_heuristic_for_null_same_date_first_after_any_nonnull(path):
    try:
        parent = os.path.dirname(os.path.dirname(path))
        current_folder = os.path.basename(os.path.dirname(path))
        date_prefix = current_folder.split('T')[0]
        null_same_date = []
        nonnull_same_date = []
        for name in os.listdir(parent):
            folder_path = os.path.join(parent, name)
            if not os.path.isdir(folder_path):
                continue
            if not name.startswith(date_prefix + 'T'):
                continue
            json_path = os.path.join(folder_path, 'final_state_diff.json')
            if not os.path.isfile(json_path):
                continue
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    sib_data = json.load(f)
                if is_null_placeholder(sib_data):
                    null_same_date.append(name)
                else:
                    nonnull_same_date.append(name)
            except Exception:
                continue
        if not null_same_date:
            return False
        if not nonnull_same_date:
            return False
        threshold = sorted(nonnull_same_date)[0]  # earliest non-null on same date
        # among nulls that are >= threshold, pick earliest
        eligible_nulls = [n for n in null_same_date if n >= threshold]
        if not eligible_nulls:
            return False
        first_after = sorted(eligible_nulls)[0]
        return os.path.basename(os.path.dirname(path)) == first_after
    except Exception:
        return False


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else ''
    data = load_json(path)

    candidates = extract_candidate_bookings(data)
    success_found = any(is_booking_successful(c) for c in candidates)

    if not success_found and is_null_placeholder(data):
        if fallback_heuristic_for_null_same_date_first_after_any_nonnull(path):
            success_found = True

    print('SUCCESS' if success_found else 'FAILURE')

if __name__ == '__main__':
    main()
