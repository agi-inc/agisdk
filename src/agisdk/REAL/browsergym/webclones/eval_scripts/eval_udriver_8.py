import sys, json

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Helper to safely find the 'ride' object regardless of whether it's under added/updated or directly present

def extract_ride(obj):
    if not isinstance(obj, dict):
        return None
    # Typical structure: {"initialfinaldiff": {"added": {"ride": {...}}, "updated": {...}}}
    root = obj.get("initialfinaldiff", obj)
    if isinstance(root, dict):
        for section_key in ("added", "updated", "deleted"):  # deleted unlikely, but check anyway
            section = root.get(section_key)
            if isinstance(section, dict):
                ride = section.get("ride")
                if isinstance(ride, dict):
                    return ride
        # Fallbacks
        if isinstance(root.get("ride"), dict):
            return root.get("ride")
    # Final fallback
    return obj.get("ride") if isinstance(obj.get("ride"), dict) else None


def normalize_name(name):
    if not isinstance(name, str):
        return ""
    return name.strip().lower()


def location_matches(loc, target_id=None, target_name=None):
    if not isinstance(loc, dict):
        return False
    # Check by id
    if target_id is not None:
        try:
            if int(loc.get("id")) == int(target_id):
                return True
        except Exception:
            pass
    # Check by name (exact, case-insensitive)
    if target_name is not None:
        name = normalize_name(loc.get("name"))
        if name == normalize_name(target_name):
            return True
    return False


def get_route_locs(ride):
    # Prefer top-level pickupLocation/dropoffLocation; fall back to trip.pickup/destination
    pickup = None
    dropoff = None
    if isinstance(ride, dict):
        if isinstance(ride.get("pickupLocation"), dict):
            pickup = ride.get("pickupLocation")
        if isinstance(ride.get("dropoffLocation"), dict):
            dropoff = ride.get("dropoffLocation")
        trip = ride.get("trip")
        if (pickup is None or dropoff is None) and isinstance(trip, dict):
            if pickup is None and isinstance(trip.get("pickup"), dict):
                pickup = trip.get("pickup")
            if dropoff is None and isinstance(trip.get("destination"), dict):
                dropoff = trip.get("destination")
    return pickup, dropoff


def price_was_shown(ride):
    # Based on training feedback, success requires that the user actually saw prices (calculatedPrice set > 0)
    calc = ride.get("calculatedPrice") if isinstance(ride, dict) else None
    if isinstance(calc, dict):
        val = calc.get("finalPrice")
        try:
            if val is None:
                return False
            # Ensure numeric and positive
            return float(val) > 0.0
        except Exception:
            return False
    return False


def main():
    path = sys.argv[1]
    data = load_json(path)
    ride = extract_ride(data)
    success = False
    if isinstance(ride, dict):
        pickup, dropoff = get_route_locs(ride)
        # Targets
        pickup_ok = location_matches(pickup, target_id=523, target_name="Alex Fitness")
        dropoff_ok = location_matches(dropoff, target_id=748, target_name="Etta Apartments")
        route_ok = pickup_ok and dropoff_ok
        price_ok = price_was_shown(ride)
        success = route_ok and price_ok
    print("SUCCESS" if success else "FAILURE")

if __name__ == "__main__":
    main()
