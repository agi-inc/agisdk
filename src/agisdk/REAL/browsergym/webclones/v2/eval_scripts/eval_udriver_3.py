import sys, json

def get_nested(d, *keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur

# Task: Book a ride from Alchemist Bar & Lounge to El Corazon Gallery
# Verification strategy:
# - A successful booking must create an entry in ride.trips with pickup=Alchemist and destination=El Corazon.
# - Accept status 'completed' or 'in progress'. Do NOT count ride.trip or bookedTrip alone (pre-booking/scheduling) as success.
# - Match by case-insensitive name or by known IDs (pickup id=177, destination id=389). Be resilient to missing fields.

ALCHEMIST_NAME = "alchemist bar & lounge"
ALCHEMIST_ID = 177
ELCORAZON_NAME = "el corazon gallery"
ELCORAZON_ID = 389

try:
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

root = data
iff = root.get("initialfinaldiff") or {}
# ride could be under added.ride typically
ride = get_nested(iff, "added", "ride") or get_nested(iff, "updated", "ride") or {}

trips = ride.get("trips")
if not isinstance(trips, list):
    trips = []

# Helper to match a location object to Alchemist or El Corazon

def is_alchemist(loc):
    if not isinstance(loc, dict):
        return False
    # ID match
    try:
        if int(loc.get("id")) == ALCHEMIST_ID:
            return True
    except Exception:
        pass
    # Name match
    name = (loc.get("name") or "").strip().lower()
    if name == ALCHEMIST_NAME:
        return True
    # formatted address heuristic
    fmt = (loc.get("formattedAddress") or loc.get("address") or "").lower()
    if "679 3rd" in fmt and "san francisco" in fmt:
        return True
    return False


def is_el_corazon(loc):
    if not isinstance(loc, dict):
        return False
    # ID match
    try:
        if int(loc.get("id")) == ELCORAZON_ID:
            return True
    except Exception:
        pass
    # Name match
    name = (loc.get("name") or "").strip().lower()
    if name == ELCORAZON_NAME:
        return True
    # formatted address heuristic
    fmt = (loc.get("formattedAddress") or loc.get("address") or "").lower()
    if "4889 mission" in fmt and "san francisco" in fmt:
        return True
    return False

success = False
valid_status = {"completed", "in progress"}
for t in trips:
    if not isinstance(t, dict):
        continue
    pickup = t.get("pickup")
    dest = t.get("destination")
    status = (t.get("status") or "").strip().lower()
    if status not in valid_status:
        continue
    if is_alchemist(pickup) and is_el_corazon(dest):
        success = True
        break

# Explicitly ignore bookedTrip-only scenarios (scheduled rides) by requiring trips evidence above.
print("SUCCESS" if success else "FAILURE")
