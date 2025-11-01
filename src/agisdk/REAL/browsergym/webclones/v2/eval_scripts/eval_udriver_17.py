import json, sys, re

# Strategy:
# 1) Locate the ride object from initialfinaldiff (prefer added.ride, then updated.ride).
# 2) Verify pickup/dropoff names match target addresses; verify date/time match target using normalization.
# 3) Confirm a price was shown (calculatedPrice.finalPrice or bookedTrip/trip.car.finalPrice > 0).
# Print SUCCESS only if all checks pass; otherwise FAILURE.

def get_in(d, path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def find_ride(data):
    # Typical path
    ride = get_in(data, ["initialfinaldiff", "added", "ride"]) 
    if isinstance(ride, dict):
        return ride
    ride = get_in(data, ["initialfinaldiff", "updated", "ride"]) 
    if isinstance(ride, dict):
        return ride
    # Fallbacks
    ride = get_in(data, ["ride"]) 
    if isinstance(ride, dict):
        return ride
    return None


def normalize_date(s):
    if not isinstance(s, str):
        return None
    m = re.match(r"\s*0*(\d{1,2})/0*(\d{1,2})/0*(\d{4})\s*$", s)
    if not m:
        return None
    month, day, year = m.groups()
    return f"{int(month)}/{int(day)}/{int(year)}"


def normalize_time(s):
    if not isinstance(s, str):
        return None
    m = re.match(r"\s*0*(\d{1,2}):(\d{2})\s*([AaPp][Mm])\s*$", s)
    if not m:
        return None
    hour, minute, mer = m.groups()
    return f"{int(hour)}:{minute} {mer.upper()}"


def get_field(ride):
    # Pickup name
    pickup_name = (
        get_in(ride, ["pickupLocation", "name"]) or
        get_in(ride, ["bookedTrip", "pickup", "name"]) or
        get_in(ride, ["trip", "pickup", "name"]) 
    )
    # Dropoff name
    drop_name = (
        get_in(ride, ["dropoffLocation", "name"]) or
        get_in(ride, ["bookedTrip", "destination", "name"]) or
        get_in(ride, ["trip", "destination", "name"]) 
    )
    # Date
    date_val = (
        get_in(ride, ["pickupDate"]) or
        get_in(ride, ["bookedTrip", "date"]) or
        get_in(ride, ["trip", "date"]) 
    )
    # Time (prefer explicit time fields; avoid trip.time which can be a date in some states)
    time_val = (
        get_in(ride, ["pickupTime"]) or
        get_in(ride, ["bookedTrip", "time"]) or
        get_in(ride, ["trip", "time"])  # fallback; may be date-like, normalization will fail then
    )
    # Price
    price = None
    cand_prices = [
        get_in(ride, ["calculatedPrice", "finalPrice"]),
        get_in(ride, ["bookedTrip", "car", "finalPrice"]),
        get_in(ride, ["trip", "car", "finalPrice"]),
    ]
    for p in cand_prices:
        try:
            if p is not None and float(p) > 0:
                price = float(p)
                break
        except (ValueError, TypeError):
            continue
    return pickup_name, drop_name, date_val, time_val, price


def matches_name(actual, expected):
    if not isinstance(actual, str):
        return False
    return actual.strip().casefold() == expected.strip().casefold()


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    ride = find_ride(data)
    if not isinstance(ride, dict):
        print("FAILURE")
        return

    pickup_name, drop_name, date_val, time_val, price = get_field(ride)

    # Target values
    target_pickup = "333 Fremont Apartments"
    target_drop = "201 Turk Street Apartments"
    target_date = "7/18/2024"
    target_time = "3:30 PM"

    # Normalize and compare
    date_ok = normalize_date(date_val) == normalize_date(target_date)
    time_ok = normalize_time(time_val) == normalize_time(target_time)
    pickup_ok = matches_name(pickup_name, target_pickup)
    drop_ok = matches_name(drop_name, target_drop)
    price_ok = (price is not None and price > 0)

    if pickup_ok and drop_ok and date_ok and time_ok and price_ok:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
