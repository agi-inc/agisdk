import json
import re
import sys


def load_json(path):
    with open(path) as f:
        return json.load(f)


# Strategy in code:
# - Find booking object from diff (prefer added, then updated)
# - Inspect bookingDetails entries: success if any reservation has Italian cuisine AND time in 3 PM hour
# - Time parsing robust to formats like "3 PM", "3:00 PM", "3:30PM", and 24h like "15:00"


def get_booking_obj(data):
    root = data
    booking = None
    try:
        booking = root.get("initialfinaldiff", {}).get("added", {}).get("booking")
    except Exception:
        booking = None
    if booking is None:
        booking = root.get("initialfinaldiff", {}).get("updated", {}).get("booking")
    if booking is None:
        booking = root.get("booking")
    return booking


def iter_booking_details(booking):
    if not booking:
        return []
    bd = booking.get("bookingDetails")
    if not bd:
        return []
    # bookingDetails could be a dict keyed by strings like "0" or a list
    if isinstance(bd, dict):
        return list(bd.values())
    if isinstance(bd, list):
        return bd
    return []


def normalize_str(s):
    return s.strip().lower() if isinstance(s, str) else ""


def is_italian(restaurant: dict) -> bool:
    if not isinstance(restaurant, dict):
        return False
    ft = restaurant.get("food_type")
    if isinstance(ft, str) and "italian" in ft.strip().lower():
        return True
    # Fallback heuristics if food_type missing: look into description/name
    desc = restaurant.get("description")
    name = restaurant.get("name")
    for v in (desc, name):
        if isinstance(v, str) and "italian" in v.strip().lower():
            return True
    return False


def parse_time_3pmish(tval: str) -> bool:
    if not isinstance(tval, str):
        return False
    s = tval.strip()
    if not s:
        return False
    # Try 12-hour format with optional minutes and optional space before AM/PM
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*([AaPp][Mm])$", s)
    if m:
        hour = int(m.group(1))
        ampm = m.group(3).upper()
        return ampm == "PM" and hour == 3
    # Try 12-hour format without space like 3PM or 3:30PM
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?([AaPp][Mm])$", s)
    if m:
        hour = int(m.group(1))
        ampm = m.group(3).upper()
        return ampm == "PM" and hour == 3
    # Try 24-hour format HH:MM or HH.MM
    m = re.match(r"^(\d{1,2})[:.](\d{2})$", s)
    if m:
        hour = int(m.group(1))
        return hour == 15
    # Try integer hour like "15"
    if s.isdigit():
        return int(s) == 15 or int(s) == 3  # ambiguous, but likely not used
    # As a last resort, simple containment check
    s_low = s.lower().replace(" ", "")
    if s_low.startswith("3") and "pm" in s_low:
        return True
    return False


def get_time_from_detail(detail, booking):
    # Prefer detail time; fallback to booking time
    t = None
    if isinstance(detail, dict):
        t = detail.get("time")
    if not t and isinstance(booking, dict):
        t = booking.get("time")
    return t


def has_error(data):
    cfg = data.get("initialfinaldiff", {}).get("added", {}).get("config", {})
    if not cfg:
        cfg = data.get("initialfinaldiff", {}).get("updated", {}).get("config", {})
    od = cfg.get("open_dining", {}) if isinstance(cfg, dict) else {}
    if isinstance(od, dict):
        if od.get("error_booking") is True:
            return True
    return False


def main(path):
    data = load_json(path)
    if has_error(data):
        print("FAILURE")
        return
    booking = get_booking_obj(data)
    details = iter_booking_details(booking)

    success = False
    for d in details:
        rest = d.get("restaurant", {}) if isinstance(d, dict) else {}
        if not is_italian(rest):
            continue
        t = get_time_from_detail(d, booking)
        if parse_time_3pmish(t):
            success = True
            break

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main(sys.argv[1])
