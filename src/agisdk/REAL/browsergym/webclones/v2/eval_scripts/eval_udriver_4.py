import json
import sys

# Verification logic for: Show me rides from 1000 Chestnut St to Rooftop 25 and book one of the rides.
# Strategy:
# 1) Success if there's a completed trip in ride.trips where pickup contains "1000 Chestnut" and destination contains "Rooftop 25".
# 2) Fallback: If wallet has a debit transaction mentioning "Rooftop 25" AND the route shown in ride (trip or pickup/dropoff) matches the same pickup/destination, count as success.


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_sections(data):
    sections = []
    if isinstance(data, dict) and "initialfinaldiff" in data:
        if isinstance(data["initialfinaldiff"], dict):
            for k in ["added", "updated"]:
                sec = data["initialfinaldiff"].get(k)
                if isinstance(sec, dict):
                    sections.append(sec)
    else:
        if isinstance(data, dict):
            sections.append(data)
    return sections if sections else [data]


def recursive_find(obj, key):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, dict):
                return v
            found = recursive_find(v, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = recursive_find(item, key)
            if found is not None:
                return found
    return None


def find_first_with_key(sections, key):
    for sec in sections:
        if isinstance(sec, dict) and key in sec and isinstance(sec[key], dict):
            return sec[key]
    for sec in sections:
        found = recursive_find(sec, key)
        if found is not None:
            return found
    return None


def text_contains(s, needle):
    if not isinstance(s, str):
        return False
    return needle in s.lower()


def location_matches(loc, needle):
    if not isinstance(loc, dict):
        return False
    low = needle.lower()
    fields = [loc.get("name"), loc.get("formattedAddress"), loc.get("address")]
    for f in fields:
        if text_contains(f, low):
            return True
    # also check nested addressComponents street if available
    ac = loc.get("addressComponents")
    if isinstance(ac, dict):
        for f in [
            ac.get("street"),
            ac.get("city"),
            ac.get("state"),
            ac.get("zipCode"),
            ac.get("country"),
        ]:
            if text_contains(f, low):
                return True
    return False


def route_shown_correct(ride):
    # Checks if the current selection shows the requested route (pickup 1000 Chestnut, destination Rooftop 25)
    if not isinstance(ride, dict):
        return False
    # Prefer ride.trip if present
    trip = ride.get("trip")
    if isinstance(trip, dict):
        p = trip.get("pickup")
        d = trip.get("destination")
        if location_matches(p, "1000 chestnut") and location_matches(d, "rooftop 25"):
            return True
    # Fall back to pickupLocation/dropoffLocation if present
    p2 = ride.get("pickupLocation")
    d2 = ride.get("dropoffLocation")
    if location_matches(p2, "1000 chestnut") and location_matches(d2, "rooftop 25"):
        return True
    return False


def completed_trip_correct(ride):
    # Search ride.trips for a completed trip with the requested route
    if not isinstance(ride, dict):
        return False
    trips = ride.get("trips")
    if not isinstance(trips, list):
        return False
    for t in trips:
        if not isinstance(t, dict):
            continue
        status = str(t.get("status", "")).lower()
        if status != "completed":
            continue
        pickup = t.get("pickup")
        dest = t.get("destination")
        if location_matches(pickup, "1000 chestnut") and location_matches(dest, "rooftop 25"):
            return True
    return False


def wallet_has_rooftop_debit(user):
    # Check wallet transactions for a debit related to Rooftop 25
    if not isinstance(user, dict):
        return False
    wallet = user.get("wallet")
    if not isinstance(wallet, dict):
        return False
    txs = wallet.get("transactions")
    if not isinstance(txs, list):
        return False
    for tx in txs:
        if not isinstance(tx, dict):
            continue
        ttype = str(tx.get("type", "")).lower()
        desc = tx.get("description", "")
        if ttype == "debit" and text_contains(desc, "rooftop 25"):
            return True
    return False


def main():
    path = sys.argv[1]
    data = load_json(path)
    sections = get_sections(data)
    ride = find_first_with_key(sections, "ride")
    user = find_first_with_key(sections, "user")

    # Primary condition: a completed trip with correct route exists
    if completed_trip_correct(ride):
        print("SUCCESS")
        return

    # Fallback: wallet shows debit to Rooftop 25 and the route shown in the UI matches the requested route
    if wallet_has_rooftop_debit(user) and route_shown_correct(ride):
        print("SUCCESS")
        return

    print("FAILURE")


if __name__ == "__main__":
    main()
