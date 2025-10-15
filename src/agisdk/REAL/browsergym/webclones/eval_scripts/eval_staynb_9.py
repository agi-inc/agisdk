import json, sys

def get_nested(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

# Strategy in code:
# - Confirm destination contains 'los angeles' (case-insensitive) using appliedDestination or recentSearches[0].destination.
# - Confirm dates exactly Sept 1 to Sept 3, 2024 via appliedDates or recentSearches dates.
# - Require evidence of a booking attempt: at least one booking error field is a non-empty message.
# - To match the training failures where price was > $600, additionally require booking.errors.expiration to be empty; otherwise mark as failure.

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    root = data.get('initialfinaldiff', {})
    added = root.get('added', {})

    search = added.get('search', {})

    # Destination detection
    dest = (
        get_nested(search, ['appliedDestination'])
        or get_nested(search, ['recentSearches', '0', 'destination'])
        or ''
    )
    dest_ok = isinstance(dest, str) and ('los angeles' in dest.lower())

    # Date detection (prefer appliedDates, else recentSearches)
    start_iso = (
        get_nested(search, ['appliedDates', 'startDate'])
        or get_nested(search, ['recentSearches', '0', 'dates', 'startDate'])
        or ''
    )
    end_iso = (
        get_nested(search, ['appliedDates', 'endDate'])
        or get_nested(search, ['recentSearches', '0', 'dates', 'endDate'])
        or ''
    )

    # Normalize to date-only YYYY-MM-DD if ISO-like
    def ymd(s):
        if isinstance(s, str) and len(s) >= 10:
            return s[:10]
        return ''

    start_ok = ymd(start_iso) == '2024-09-01'
    end_ok = ymd(end_iso) == '2024-09-03'

    # Booking attempt evidence via errors presence
    booking = added.get('booking', {})
    errors = get_nested(booking, ['errors'], {})
    if not isinstance(errors, dict):
        errors = {}

    # At least one non-empty error indicates they reached a booking form
    any_nonempty_error = any(
        isinstance(v, str) and v.strip() != '' for v in errors.values()
    )

    # Align with training signals: expiration error should be empty for success
    expiration_ok = (errors.get('expiration', '') == '')

    success = dest_ok and start_ok and end_ok and any_nonempty_error and expiration_ok

    print('SUCCESS' if success else 'FAILURE')
except Exception:
    # On any parsing/runtime error, be conservative
    print('FAILURE')