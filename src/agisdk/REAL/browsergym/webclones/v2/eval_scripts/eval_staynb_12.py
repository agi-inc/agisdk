import json, sys

def extract_search(data):
    # Try to find the search object from added or updated diffs
    try:
        diffs = data.get('initialfinaldiff', {})
    except AttributeError:
        return {}
    added = diffs.get('added', {}) or {}
    updated = diffs.get('updated', {}) or {}
    search_added = added.get('search', {}) or {}
    search_updated = updated.get('search', {}) or {}
    # Merge with updated taking precedence
    merged = {}
    if isinstance(search_added, dict):
        merged.update(search_added)
    if isinstance(search_updated, dict):
        merged.update(search_updated)
    return merged


def extract_booking(data):
    """Extract booking object from added or updated diffs"""
    try:
        diffs = data.get('initialfinaldiff', {})
    except AttributeError:
        return {}
    added = diffs.get('added', {}) or {}
    updated = diffs.get('updated', {}) or {}
    booking_added = added.get('booking', {}) or {}
    booking_updated = updated.get('booking', {}) or {}
    # Merge with updated taking precedence
    merged = {}
    if isinstance(booking_added, dict):
        merged.update(booking_added)
    if isinstance(booking_updated, dict):
        merged.update(booking_updated)
    return merged


def get_first_recent(search_obj):
    recent = search_obj.get('recentSearches')
    if isinstance(recent, dict):
        # recentSearches can have numeric string keys
        if '0' in recent and isinstance(recent['0'], dict):
            return recent['0']
        # fallback: first item by sorted key
        for k in sorted(recent.keys()):
            if isinstance(recent[k], dict):
                return recent[k]
    return None


def normalize_date_str(v):
    if not isinstance(v, str):
        return None
    # Take YYYY-MM-DD
    if len(v) >= 10:
        return v[:10]
    return v


def main():
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    search = extract_search(data)
    booking = extract_booking(data)

    # Destination
    dest = search.get('appliedDestination')
    if not isinstance(dest, str) or not dest.strip():
        first_recent = get_first_recent(search)
        if first_recent and isinstance(first_recent.get('destination'), str):
            dest = first_recent.get('destination')

    dest_ok = False
    if isinstance(dest, str):
        dlow = dest.lower()
        if ('delhi' in dlow) and ('india' in dlow):
            dest_ok = True

    # Dates
    dates = search.get('appliedDates')
    if not isinstance(dates, dict):
        first_recent = get_first_recent(search)
        if first_recent and isinstance(first_recent.get('dates'), dict):
            dates = first_recent.get('dates')
    start = normalize_date_str(dates.get('startDate')) if isinstance(dates, dict) else None
    end = normalize_date_str(dates.get('endDate')) if isinstance(dates, dict) else None
    dates_ok = (start == '2024-09-07' and end == '2024-09-09')

    # Guests
    guests_ok = False
    guest_counts = search.get('appliedGuestCounts')
    if isinstance(guest_counts, dict):
        adults = guest_counts.get('Adults')
        try:
            adults_num = int(adults)
        except (TypeError, ValueError):
            adults_num = None
        if adults_num == 2:
            guests_ok = True
    else:
        # Fallback to recentSearches guest string
        first_recent = get_first_recent(search)
        gstr = first_recent.get('guests') if first_recent else None
        if isinstance(gstr, str):
            # Extract leading integer
            num = None
            for token in gstr.split():
                if token.isdigit():
                    num = int(token)
                    break
            if num == 2:
                guests_ok = True

    # Check that NO booking was initiated (task only asks to "show" places, not book)
    booking_ok = True
    if isinstance(booking, dict):
        # If isBooking is True, that's a failure
        if booking.get('isBooking') is True:
            booking_ok = False
        # If currentBooking exists and is not None, that's a failure
        if booking.get('currentBooking') is not None:
            booking_ok = False
        # If there are payment errors, it means booking flow was entered
        errors = booking.get('errors', {})
        if isinstance(errors, dict):
            # Check if any error fields have been populated/validated
            # (empty string means field was checked but valid, non-empty means error)
            for field in ['cardNumber', 'expiration', 'cvv', 'zipcode']:
                if errors.get(field):  # Non-empty error message
                    booking_ok = False
                    break

    if dest_ok and dates_ok and guests_ok and booking_ok:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()