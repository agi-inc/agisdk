import json
import sys

# Verification logic for task:
# - Destination should be Cape Town
# - Dates should be Oct 1, 2024 to Oct 6, 2024 (inclusive of bounds)
# - Total guests (Adults + Children) should equal 4
# - A place should be added to a wishlist which meets constraints: bedrooms >= 2 and beds >= 2
# - Wifi amenity is not present in available data; thus we verify the actual outcome (the selected stay meets constraints)
#   rather than the presence of a filter flag.


def get_nested(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def normalize_date(s):
    if not isinstance(s, str):
        return None
    # Expect ISO string; compare first 10 chars (YYYY-MM-DD)
    return s[:10]


def compute_total_guests(guest_counts):
    if not isinstance(guest_counts, dict):
        return None
    adults = guest_counts.get("Adults", 0) or 0
    children = guest_counts.get("Children", 0) or 0
    # Typically infants/pets are not counted as guests for capacity
    return adults + children


def parse_guests_string(guest_str):
    # Fallback: parse like "4 Guests" or "1 Guest"
    if not isinstance(guest_str, str):
        return None
    parts = guest_str.strip().split()
    for p in parts:
        try:
            return int(p)
        except:
            pass
    return None


def any_stay_meets_requirements(wishlist_data):
    # Iterate all wishlists and their stays; ensure at least one stay has bedrooms >=2 and beds >=2
    if not isinstance(wishlist_data, dict):
        return False
    wishlists = wishlist_data.get("wishlists")
    if not isinstance(wishlists, dict):
        return False
    found_any = False
    for wl in wishlists.values():
        stays = None
        if isinstance(wl, dict):
            stays = wl.get("stays")
        if isinstance(stays, list):
            for stay in stays:
                rooms = stay.get("rooms") if isinstance(stay, dict) else None
                if isinstance(rooms, dict):
                    bedrooms = rooms.get("bedrooms")
                    beds = rooms.get("beds")
                    try:
                        if bedrooms is not None and beds is not None:
                            if int(bedrooms) >= 2 and int(beds) >= 2:
                                found_any = True
                                return True
                    except Exception:
                        # If not integers, skip
                        continue
    return found_any


def main():
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)

    root = data
    # The examples show data under initialfinaldiff.added
    added = get_nested(root, ["initialfinaldiff", "added"], {})
    search = added.get("search", {}) if isinstance(added, dict) else {}
    wishlist = added.get("wishlist", {}) if isinstance(added, dict) else {}

    # Destination check (prefer appliedDestination, fallback to recentSearches[0].destination)
    dest = search.get("appliedDestination")
    if not dest:
        recent_searches = search.get("recentSearches")
        if isinstance(recent_searches, dict) and recent_searches:
            first_key = sorted(recent_searches.keys(), key=lambda x: str(x))[0]
            rs = recent_searches.get(first_key, {})
            dest = rs.get("destination")
    dest_ok = isinstance(dest, str) and ("cape town" in dest.lower())

    # Dates check (prefer appliedDates)
    dates = search.get("appliedDates") if isinstance(search, dict) else None
    if not isinstance(dates, dict) or not dates:
        # fallback to recentSearches
        recent_searches = search.get("recentSearches")
        if isinstance(recent_searches, dict) and recent_searches:
            first_key = sorted(recent_searches.keys(), key=lambda x: str(x))[0]
            rs = recent_searches.get(first_key, {})
            dates = rs.get("dates", {}) if isinstance(rs, dict) else {}
    start = normalize_date(dates.get("startDate") if isinstance(dates, dict) else None)
    end = normalize_date(dates.get("endDate") if isinstance(dates, dict) else None)
    dates_ok = start == "2024-10-01" and end == "2024-10-06"

    # Guests check (prefer appliedGuestCounts)
    guest_counts = search.get("appliedGuestCounts") if isinstance(search, dict) else None
    total_guests = compute_total_guests(guest_counts) if guest_counts else None
    if total_guests is None:
        # fallback parse from recent searches string
        recent_searches = search.get("recentSearches")
        guest_str = None
        if isinstance(recent_searches, dict) and recent_searches:
            first_key = sorted(recent_searches.keys(), key=lambda x: str(x))[0]
            rs = recent_searches.get(first_key, {})
            guest_str = rs.get("guests") if isinstance(rs, dict) else None
        total_guests = parse_guests_string(guest_str)
    guests_ok = total_guests == 4

    # Wishlist check: a stay added that meets bedrooms>=2 and beds>=2
    stay_ok = any_stay_meets_requirements(wishlist)

    if dest_ok and dates_ok and guests_ok and stay_ok:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
