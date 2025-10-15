import json, sys

# Task: Verify an UberXL ride was ordered from 77 Bluxome Apartments to Anza Branch Library.
# Approach:
# - Load final_state_diff.json and extract the 'ride' object from typical locations.
# - Determine SUCCESS if the ride.trips array contains a trip with:
#     * status in {"in progress", "completed"}
#     * car.type == "UdriverXL"
#     * pickup corresponds to 77 Bluxome Apartments (id 715 or matching name/address)
#     * destination corresponds to Anza Branch Library (id 499 or matching name/address)
# - Otherwise, print FAILURE.
# Rationale: Checking trips ensures an actual booking was made (avoids false positives like viewing options only).


def deep_get(dct, *keys):
    cur = dct
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def extract_ride(data):
    # Try several common paths to get the ride structure
    paths = [
        ("initialfinaldiff", "added", "ride"),
        ("added", "ride"),
        ("ride",),
    ]
    for p in paths:
        r = deep_get(data, *p)
        if isinstance(r, dict):
            return r
    return None


def norm(s):
    if isinstance(s, str):
        return s.strip().lower()
    return ""


def is_bluxome(pickup):
    if not isinstance(pickup, dict):
        return False
    pid = pickup.get("id")
    if pid == 715:
        return True
    name = norm(pickup.get("name"))
    fmt = norm(pickup.get("formattedAddress"))
    addr = norm(pickup.get("address"))
    # Check name or any address field containing bluxome
    if "77 bluxome" in name or "77 bluxome" in fmt or "77 bluxome" in addr:
        return True
    if name == "77 bluxome apartments":
        return True
    return False


def is_anza(dest):
    if not isinstance(dest, dict):
        return False
    did = dest.get("id")
    if did == 499:
        return True
    name = norm(dest.get("name"))
    fmt = norm(dest.get("formattedAddress"))
    addr = norm(dest.get("address"))
    if "anza branch library" in name or "anza branch library" in fmt or "anza branch library" in addr:
        return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    ride = extract_ride(data)
    if not isinstance(ride, dict):
        print("FAILURE")
        return

    trips = ride.get("trips")
    if not isinstance(trips, list):
        trips = []

    success = False
    for t in trips:
        if not isinstance(t, dict):
            continue
        status = norm(t.get("status"))
        if status not in {"in progress", "completed"}:
            continue
        car = t.get("car", {}) if isinstance(t.get("car"), dict) else {}
        car_type = norm(car.get("type"))
        if car_type != "udriverxl":
            continue
        pickup = t.get("pickup", {})
        dest = t.get("destination", {})
        if is_bluxome(pickup) and is_anza(dest):
            success = True
            break

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
