import sys, json

def extract_nested(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def parse_iso_date(date_str):
    # Expect formats like '2024-10-14T00:00:00.000Z'
    if not isinstance(date_str, str):
        return None
    try:
        date_part = date_str.split('T')[0]
        y, m, d = date_part.split('-')
        return int(y), int(m), int(d)
    except Exception:
        return None


def get_section(diff, key):
    for sect in ("updated", "added"):
        if isinstance(diff.get(sect), dict) and key in diff[sect]:
            return diff[sect][key]
    return None


def has_booking_indicators(diff_root):
    # Look for evidence of booking flow beyond search (e.g., selectedRoom, bookingNumber, userInfoForm, cardForm, agreement)
    indicators = {"bookingNumber", "selectedRoom", "userInfoForm", "cardForm", "policyAgreement", "isGuestFormValid"}
    for sect in ("updated", "added"):
        sect_obj = diff_root.get(sect)
        if isinstance(sect_obj, dict) and "guest" in sect_obj:
            guest_obj = sect_obj.get("guest")
            if isinstance(guest_obj, dict):
                for key in indicators:
                    if key in guest_obj:
                        # Presence of any of these implies going into booking/checkout
                        return True
    return False


def main():
    path = sys.argv[1]
    try:
        data = json.load(open(path, 'r'))
    except Exception:
        print("FAILURE")
        return

    diff_root = data.get("initialfinaldiff", {})
    # If booking indicators present, this should be FAILURE for this task (should only show hotels)
    if has_booking_indicators(diff_root):
        print("FAILURE")
        return

    search_obj = get_section(diff_root, "search")
    if not isinstance(search_obj, dict):
        print("FAILURE")
        return

    # Prefer lastSearchCriteria when available, else fall back to direct search
    lsc = search_obj.get("lastSearchCriteria") if isinstance(search_obj.get("lastSearchCriteria"), dict) else None
    base = lsc if lsc else search_obj

    # Destination must be Tokyo
    dest = base.get("destination")
    if not isinstance(dest, str) or ("tokyo" not in dest.lower()):
        print("FAILURE")
        return

    # Dates must span from the 14th to 20th; training includes September and October 2024.
    dates = base.get("dates") if isinstance(base.get("dates"), dict) else None
    if not dates:
        print("FAILURE")
        return

    start = parse_iso_date(dates.get("startDate"))
    end = parse_iso_date(dates.get("endDate"))
    if not start or not end:
        print("FAILURE")
        return

    sy, sm, sd = start
    ey, em, ed = end

    # Ensure correct days and month/year consistent with training examples
    # Accept either September (9) or October (10) 2024, start day 14, end day 20
    valid_month = (sm in (9, 10)) and (em in (9, 10)) and (sm == em)
    valid_year = (sy == 2024 and ey == 2024)
    valid_days = (sd == 14 and ed == 20)

    if not (valid_month and valid_year and valid_days):
        print("FAILURE")
        return

    # Guests/Rooms: require 1 room if available
    guests = base.get("guests") if isinstance(base.get("guests"), dict) else None
    rooms_ok = False
    adults_ok = True  # default to True if not present; if present, allow 3 or 4 based on training variability
    if guests:
        rooms = guests.get("Rooms")
        if rooms is not None:
            rooms_ok = (rooms == 1)
        adults = guests.get("Adults")
        if adults is not None:
            adults_ok = adults in (3, 4)

    # If rooms field not present at all in either base, try the other source (search vs lastSearchCriteria)
    if not rooms_ok:
        other = search_obj if base is lsc else lsc  # check the other source
        if isinstance(other, dict):
            og = other.get("guests") if isinstance(other.get("guests"), dict) else None
            if og and og.get("Rooms") is not None:
                rooms_ok = (og.get("Rooms") == 1)
            if og and og.get("Adults") is not None:
                adults_ok = (og.get("Adults") in (3, 4))

    # Must have rooms_ok True (explicitly 1 room). Adults variability allowed but if present must be 3 or 4
    if not rooms_ok or not adults_ok:
        print("FAILURE")
        return

    print("SUCCESS")

if __name__ == "__main__":
    main()
