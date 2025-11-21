import json
import sys


def norm(s):
    return (s or "").strip().lower()


def is_irving(loc):
    if not isinstance(loc, dict):
        return False
    # Strong identifiers seen in data
    if str(loc.get("identifier", "")).upper() == "SPR":
        return True
    if loc.get("id") == 129:
        return True
    name = norm(loc.get("name"))
    if name:
        # Look for explicit Irving + 22 indicators
        if "irving" in name and (
            "22nd" in name
            or "22 & " in name
            or name.startswith("22")
            or "22 & irving" in name
            or "22nd & irving" in name
        ):
            return True
    street = norm(loc.get("addressComponents", {}).get("street"))
    if street:
        if "irving" in street and ("2101" in street or "irving st" in street):
            return True
    formatted = norm(loc.get("formattedAddress"))
    if formatted and "irving st" in formatted and "san francisco" in formatted:
        return True
    address = norm(loc.get("address"))
    if address and "irving st" in address:
        return True
    return False


def is_7eleven(loc):
    if not isinstance(loc, dict):
        return False
    name = norm(loc.get("name"))
    return "7-eleven" in name


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    added = data.get("initialfinaldiff", {}).get("added", {})
    ride = added.get("ride", {}) if isinstance(added, dict) else {}
    trips = ride.get("trips", []) if isinstance(ride, dict) else []

    success = False
    if isinstance(trips, list):
        for trip in trips:
            if not isinstance(trip, dict):
                continue
            status = norm(trip.get("status"))
            if status != "completed":
                continue
            pickup = trip.get("pickup", {})
            dest = trip.get("destination", {})
            if is_irving(pickup) and is_7eleven(dest):
                success = True
                break

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    # Strategy: Validate a completed trip exists where pickup matches 22nd & Irving and destination is any 7-Eleven.
    # This avoids false positives from scheduled rides or reversed routes by checking both pickup and destination.
    main()
