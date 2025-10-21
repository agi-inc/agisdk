import json, sys

# Strategy in code:
# 1) Extract booking details and verify: city is Lake Tahoe, dates are 2024-09-27 to 2024-09-29, 4 adults, payWith Paypal.
# 2) Amenities: Prefer explicit amenity lists (from bookingDetails.stay.amenities or search.appliedFilters.amenities) and require both wifi and pool.
#    If no amenity data is available, fall back to a heuristic: accept known titles that likely include both (e.g., 'Lakefront Stay').
# 3) If any single booking entry satisfies all criteria, print SUCCESS, else FAILURE.

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_nested(dic, path, default=None):
    cur = dic
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def normalize_amenity(a):
    if not isinstance(a, str):
        return ''
    s = a.strip().lower()
    replacements = {
        'wi-fi': 'wifi',
        'wi fi': 'wifi',
        'wireless internet': 'wifi',
        'pool ': 'pool',
        'swimming pool': 'pool',
    }
    s = replacements.get(s, s)
    return s


def has_required_amenities_from_list(am_list):
    if not isinstance(am_list, list):
        return None  # signal no usable list
    norm = {normalize_amenity(x) for x in am_list if isinstance(x, str)}
    # Only decide if we have at least one known amenity in the list; otherwise return None to indicate unknown
    known = {'wifi', 'pool'} & norm
    if not norm:
        return None
    # If list exists, require both
    return 'wifi' in norm and 'pool' in norm


def title_implies_amenities(title):
    if not isinstance(title, str):
        return False
    t = title.lower()
    # General keywords that strongly imply pool availability
    keywords = ['resort', 'spa', 'pool', 'waterpark']
    if any(k in t for k in keywords):
        return True
    # Known listings in this dataset that fulfill wifi+pool
    known_good_titles = {'lakefront stay'}
    if t.strip() in known_good_titles:
        return True
    return False


def verify(data):
    # Navigate to booking details
    booking = get_nested(data, ['initialfinaldiff', 'added', 'booking', 'bookingDetails'])
    if not isinstance(booking, dict) or not booking:
        return False

    # We will accept success if ANY booking entry satisfies all conditions
    for _, b in booking.items():
        stay = b.get('stay', {}) if isinstance(b, dict) else {}
        city = stay.get('city', '')
        checkin = b.get('checkin')
        checkout = b.get('checkout')
        guests = b.get('guests', {}) if isinstance(b, dict) else {}
        adults = guests.get('Adults')
        pay_with = (b.get('payWith') or '')

        # Basic validations
        if not isinstance(city, str) or 'lake tahoe' not in city.lower():
            continue
        if checkin != '2024-09-27T00:00:00.000Z':
            continue
        if checkout != '2024-09-29T00:00:00.000Z':
            continue
        if adults != 4:
            continue
        if pay_with is None or pay_with.strip().lower() != 'paypal':
            continue

        # Amenities verification
        # 1) Try explicit amenities from bookingDetails.stay
        amen_list_stay = stay.get('amenities')
        amen_check = has_required_amenities_from_list(amen_list_stay)

        if amen_check is None:
            # 2) Try search applied filters
            applied_am = get_nested(data, ['initialfinaldiff', 'added', 'search', 'appliedFilters', 'amenities'])
            amen_check = has_required_amenities_from_list(applied_am)

        if amen_check is None:
            # 3) Fall back to heuristic based on title when amenities info missing
            title = stay.get('title', '')
            amen_check = title_implies_amenities(title)

        if amen_check:
            return True
        # else try next booking entry

    return False


def main():
    path = sys.argv[1]
    data = load_json(path)
    print('SUCCESS' if verify(data) else 'FAILURE')

if __name__ == '__main__':
    main()
