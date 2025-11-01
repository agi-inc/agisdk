import json, sys

# Strategy:
# - Validate destination is 'Paris, France', dates are 2024-10-15 to 2024-10-19, and Adults count is 3.
# - Validate amenity filters are applied (wifi, parking, AC required).
# - Prefer applied* fields; fallback to recentSearches["0"]. If any mismatch or a booking record exists, mark FAILURE.

def get_nested(dct, *keys):
    cur = dct
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

root = data
initialfinaldiff = root.get('initialfinaldiff', {})
added = initialfinaldiff.get('added', {}) if isinstance(initialfinaldiff, dict) else {}

# Extract search info, preferring added.search, then root.search
search = None
if isinstance(added, dict):
    search = added.get('search')
if search is None:
    search = root.get('search')

# Extract booking info
booking = None
if isinstance(added, dict):
    booking = added.get('booking')
if booking is None:
    booking = root.get('booking')

# If booking details exist and non-empty => FAILURE (user shouldn't have booked)
booked = False
if isinstance(booking, dict):
    bd = booking.get('bookingDetails')
    if isinstance(bd, dict) and len(bd) > 0:
        booked = True

if booked:
    print("FAILURE")
    sys.exit(0)

# Validate search criteria
required_dest = "Paris, France"
required_start = "2024-10-15"
required_end = "2024-10-19"
required_adults = 3

ok = True

# Destination
dest = None
if isinstance(search, dict):
    dest = search.get('appliedDestination')
    if not dest:
        recent = search.get('recentSearches')
        if isinstance(recent, dict):
            first = recent.get('0') or recent.get(0)
            if isinstance(first, dict):
                dest = first.get('destination')

if dest != required_dest:
    ok = False

# Dates
start_val = None
end_val = None
if isinstance(search, dict):
    ad = search.get('appliedDates')
    if isinstance(ad, dict):
        start_val = ad.get('startDate')
        end_val = ad.get('endDate')
    if not start_val or not end_val:
        recent = search.get('recentSearches')
        if isinstance(recent, dict):
            first = recent.get('0') or first.get(0)
            if isinstance(first, dict):
                dates = first.get('dates')
                if isinstance(dates, dict):
                    start_val = start_val or dates.get('startDate')
                    end_val = end_val or dates.get('endDate')

def date_matches(val, want_prefix):
    if not isinstance(val, str):
        return False
    return val.startswith(want_prefix)

if not (date_matches(start_val, required_start) and date_matches(end_val, required_end)):
    ok = False

# Guests (Adults count)
adults = None
if isinstance(search, dict):
    agc = search.get('appliedGuestCounts')
    if isinstance(agc, dict):
        adults = agc.get('Adults')
    if adults is None:
        recent = search.get('recentSearches')
        if isinstance(recent, dict):
            first = recent.get('0') or recent.get(0)
            if isinstance(first, dict):
                # recentSearches often stores 'guests' as a string like '3 Guests'; not reliable for numeric check.
                # Prefer appliedGuestCounts when available; if missing, try to parse number from string.
                guests_str = first.get('guests')
                if isinstance(guests_str, str):
                    parts = guests_str.strip().split()
                    if parts and parts[0].isdigit():
                        try:
                            adults = int(parts[0])
                        except Exception:
                            adults = None

if adults != required_adults:
    ok = False

# Amenities validation (wifi, parking, AC required)
if isinstance(search, dict):
    af = search.get('appliedFilters')
    if isinstance(af, dict):
        amenities = af.get('amenities')
        if isinstance(amenities, list) and len(amenities) > 0:
            # Normalize amenities to lowercase
            amenities_lower = [str(a).lower() for a in amenities]
            
            # Check for wifi (wifi, wi-fi, wireless internet, etc.)
            has_wifi = any(
                term in amen 
                for amen in amenities_lower 
                for term in ['wifi', 'wi-fi', 'wi fi', 'wireless']
            )
            
            # Check for parking
            has_parking = any('parking' in amen for amen in amenities_lower)
            
            # Check for AC (ac, air conditioning, a/c, climate control, etc.)
            has_ac = any(
                term in amen 
                for amen in amenities_lower 
                for term in ['ac', 'a/c', 'air conditioning', 'climate', 'air conditioned']
            )
            
            if not (has_wifi and has_parking and has_ac):
                ok = False
        else:
            # If amenities list is empty or missing, filters were not applied
            ok = False
    else:
        # If appliedFilters doesn't exist, filters were not applied
        ok = False

print("SUCCESS" if ok else "FAILURE")