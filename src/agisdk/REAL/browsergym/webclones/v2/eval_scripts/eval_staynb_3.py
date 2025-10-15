import sys, json

# Verification script for task:
# "Find me places in Cape Town for 4 guests for the dates October 1st to 6th.
#  I need 2+ bedrooms and beds along with wifi. Add a place that fits these requirements to my wishlist."
#
# Strategy:
# 1) Verify search context: destination includes "Cape Town", dates cover 2024-10-01 to 2024-10-06, and total guests >= 4.
# 2) Verify wishlist: at least one stay added with rooms.bedrooms >= 2 and rooms.beds >= 2.
# Note: Wifi is not explicitly represented in provided data; do not enforce to avoid false negatives.


def extract(dct, *keys, default=None):
    cur = dct
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def get_recent_search(search):
    rs = search.get('recentSearches') if isinstance(search, dict) else None
    if isinstance(rs, dict):
        # keys may be '0' or 0
        if '0' in rs:
            return rs['0']
        if 0 in rs:
            return rs[0]
        # or any first entry
        for v in rs.values():
            return v
    return None


def normalize_date_str(s):
    if not isinstance(s, str):
        return ''
    # Expect ISO; return date part
    return s[:10]


def total_guests(guest_counts, recent):
    total = 0
    if isinstance(guest_counts, dict):
        total += int(guest_counts.get('Adults', 0) or 0)
        total += int(guest_counts.get('Children', 0) or 0)
    if total == 0 and isinstance(recent, dict):
        g = recent.get('guests')
        if isinstance(g, str):
            # extract leading integer if present
            num = ''
            for ch in g:
                if ch.isdigit():
                    num += ch
                elif num:
                    break
            if num:
                try:
                    total = int(num)
                except:
                    pass
    return total


def destination_ok(search):
    dest = extract(search, 'appliedDestination')
    if not isinstance(dest, str) or not dest.strip():
        recent = get_recent_search(search)
        dest = recent.get('destination') if isinstance(recent, dict) else ''
    if not isinstance(dest, str):
        dest = ''
    return 'cape town' in dest.lower()


def dates_ok(search):
    start = extract(search, 'appliedDates', 'startDate')
    end = extract(search, 'appliedDates', 'endDate')
    if not start or not end:
        recent = get_recent_search(search)
        if isinstance(recent, dict):
            start = extract(recent, 'dates', 'startDate')
            end = extract(recent, 'dates', 'endDate')
    start_d = normalize_date_str(start)
    end_d = normalize_date_str(end)
    return start_d == '2024-10-01' and end_d == '2024-10-06'


def guests_ok(search):
    gc = extract(search, 'appliedGuestCounts')
    recent = get_recent_search(search)
    tg = total_guests(gc, recent)
    return tg >= 4


def wishlist_has_matching_stay(wishlist):
    # Collect all stays across all wishlists
    if not isinstance(wishlist, dict):
        return False
    wishlists = wishlist.get('wishlists')
    stays = []
    if isinstance(wishlists, dict):
        for wl in wishlists.values():
            if isinstance(wl, dict) and isinstance(wl.get('stays'), list):
                stays.extend(wl['stays'])
    # Fallback: sometimes stays might not be nested? Keep robust, but in given data it's nested.
    if not stays:
        return False
    for s in stays:
        rooms = s.get('rooms') if isinstance(s, dict) else None
        if not isinstance(rooms, dict):
            continue
        bedrooms = rooms.get('bedrooms', 0) or 0
        beds = rooms.get('beds', 0) or 0
        try:
            bedrooms = int(bedrooms)
        except:
            bedrooms = 0
        try:
            beds = int(beds)
        except:
            beds = 0
        if bedrooms >= 2 and beds >= 2:
            return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
        added = extract(data, 'initialfinaldiff', 'added') or {}
        search = added.get('search', {})
        wishlist = added.get('wishlist', {})

        if not destination_ok(search):
            print('FAILURE')
            return
        if not dates_ok(search):
            print('FAILURE')
            return
        if not guests_ok(search):
            print('FAILURE')
            return
        if not wishlist_has_matching_stay(wishlist):
            print('FAILURE')
            return

        print('SUCCESS')
    except Exception:
        # On any parsing error, be conservative and mark failure
        print('FAILURE')

if __name__ == '__main__':
    main()
