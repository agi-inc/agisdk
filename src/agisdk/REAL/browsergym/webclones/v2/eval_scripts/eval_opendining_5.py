import json
import sys


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# Helper to safely get nested keys


def get_in(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


# Extract the booking object from possible locations


def extract_booking(state):
    # Common path in examples
    booking = get_in(state, ["initialfinaldiff", "added", "booking"], None)
    if isinstance(booking, dict):
        return booking
    # Fallback to updated
    booking = get_in(state, ["initialfinaldiff", "updated", "booking"], None)
    if isinstance(booking, dict):
        return booking
    # As a last resort, try top-level 'booking'
    booking = state.get("booking") if isinstance(state, dict) else None
    if isinstance(booking, dict):
        return booking
    return None


# Extract the first booking detail entry from dict-with-numeric-keys or list


def extract_first_detail(booking):
    details = booking.get("bookingDetails") if isinstance(booking, dict) else None
    if not details:
        return None
    if isinstance(details, list):
        return details[0] if details else None
    if isinstance(details, dict):
        # Sort keys to make deterministic; keys might be numeric strings like "0"
        try:
            # Try to sort by integer value if possible
            keys = sorted(
                details.keys(),
                key=lambda k: int(k) if isinstance(k, str) and k.isdigit() else k,
            )
        except Exception:
            keys = list(details.keys())
        for k in keys:
            return details[k]
    return None


# Normalize a guest string like "2 people"


def normalize_guests(val):
    if not isinstance(val, str):
        return None
    return val.strip().lower()


# Main verification logic


def verify(state):
    booking = extract_booking(state)
    if not isinstance(booking, dict):
        return False

    detail = extract_first_detail(booking)
    if not isinstance(detail, dict):
        # No concrete booked detail -> failure
        return False

    # Check rating >= 4.0
    restaurant = detail.get("restaurant", {}) if isinstance(detail.get("restaurant"), dict) else {}
    rating_val = restaurant.get("rating")
    try:
        rating = float(rating_val)
    except Exception:
        return False
    if rating < 4.0:
        return False

    # Check guests exactly 2 people (from detail or from booking fallback)
    guests_detail = normalize_guests(detail.get("guests"))
    guests_booking = normalize_guests(booking.get("guests"))
    if guests_detail != "2 people" and guests_booking != "2 people":
        return False

    # Check occasion marked as Birthday in optionals
    optionals = detail.get("optionals") if isinstance(detail.get("optionals"), dict) else None
    occasion = optionals.get("occasion") if isinstance(optionals, dict) else None
    if not isinstance(occasion, str) or occasion.strip().lower() != "birthday":
        return False

    # Basic sanity: must have a date and time in the detail for an actual reservation
    date_ok = isinstance(detail.get("date"), str) and len(detail.get("date").strip()) > 0
    time_ok = isinstance(detail.get("time"), str) and len(detail.get("time").strip()) > 0
    if not (date_ok and time_ok):
        return False

    return True


if __name__ == "__main__":
    try:
        path = sys.argv[1]
        data = load_json(path)
        result = verify(data)
        print("SUCCESS" if result else "FAILURE")
    except Exception:
        # In case of any unexpected errors, default to FAILURE per strict verification
        print("FAILURE")
