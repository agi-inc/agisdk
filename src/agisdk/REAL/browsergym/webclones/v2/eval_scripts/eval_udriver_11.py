import json, sys

# Strategy in code comments:
# 1) Confirm the CURRENT ride.trip pickup and destination are Club X -> Fox Plaza Apartments.
# 2) Confirm a COMPLETED trip exists in ride.trips for that same route.
# 3) Confirm a WALLET debit transaction with description containing "Trip to Fox Plaza Apartments"
#    whose amount approximately matches one of the expected prices (trip.car.finalPrice, calculatedPrice.finalPrice, or the completed trip's car.finalPrice).
# Only if all three conditions are met, print SUCCESS; otherwise, FAILURE.

def normalize(s):
    return (s or "").strip().lower()

def matches_location(loc, target_name=None, target_id=None):
    if not isinstance(loc, dict):
        return False
    name_ok = normalize(loc.get("name")) == normalize(target_name) if target_name is not None else True
    id_ok = (loc.get("id") == target_id) if target_id is not None else True
    # If both target_name and target_id provided, allow match by either (names can vary in formatting)
    if target_name is not None and target_id is not None:
        return normalize(loc.get("name")) == normalize(target_name) or loc.get("id") == target_id
    return name_ok and id_ok

def approx_equal(a, b, tol=0.05):
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

idf = data.get("initialfinaldiff", {})
added = idf.get("added", {})
ride = added.get("ride", {}) if isinstance(added.get("ride", {}), dict) else {}
user = added.get("user", {}) if isinstance(added.get("user", {}), dict) else {}

ride_trip = ride.get("trip", {}) if isinstance(ride.get("trip", {}), dict) else {}
pickup = ride_trip.get("pickup", {}) if isinstance(ride_trip.get("pickup", {}), dict) else {}
dest = ride_trip.get("destination", {}) if isinstance(ride_trip.get("destination", {}), dict) else {}

# 1) Validate current trip is the correct route
current_correct = (
    matches_location(pickup, target_name="Club X", target_id=201) and
    matches_location(dest, target_name="Fox Plaza Apartments", target_id=723)
)

# 2) Look for a completed trip of the correct route
completed_trips = []
for t in ride.get("trips", []) or []:
    if not isinstance(t, dict):
        continue
    if normalize(t.get("status")) != "completed":
        continue
    tp = t.get("pickup", {}) if isinstance(t.get("pickup", {}), dict) else {}
    td = t.get("destination", {}) if isinstance(t.get("destination", {}), dict) else {}
    if matches_location(tp, target_name="Club X", target_id=201) and matches_location(td, target_name="Fox Plaza Apartments", target_id=723):
        completed_trips.append(t)

has_completed_trip = len(completed_trips) > 0

# 3) Find wallet debit transaction for Trip to Fox Plaza Apartments and match amount
wallet = user.get("wallet", {}) if isinstance(user.get("wallet", {}), dict) else {}
transactions = wallet.get("transactions", []) or []
fox_txns = []
for tx in transactions:
    if not isinstance(tx, dict):
        continue
    if normalize(tx.get("type")) != "debit":
        continue
    desc = normalize(tx.get("description"))
    if "trip to fox plaza apartments" in desc:
        fox_txns.append(tx)

has_wallet_txn = len(fox_txns) > 0

# Expected amounts to compare against
expected_amounts = []
car = ride_trip.get("car", {}) if isinstance(ride_trip.get("car", {}), dict) else {}
if isinstance(car, dict) and isinstance(car.get("finalPrice"), (int, float)):
    expected_amounts.append(float(car.get("finalPrice")))
calc = ride.get("calculatedPrice", {}) if isinstance(ride.get("calculatedPrice", {}), dict) else {}
if isinstance(calc.get("finalPrice"), (int, float)):
    expected_amounts.append(float(calc.get("finalPrice")))
for ct in completed_trips:
    ccar = ct.get("car", {}) if isinstance(ct.get("car", {}), dict) else {}
    if isinstance(ccar.get("finalPrice"), (int, float)):
        expected_amounts.append(float(ccar.get("finalPrice")))

amount_match = False
if fox_txns and expected_amounts:
    for tx in fox_txns:
        amt = tx.get("amount")
        try:
            famt = float(amt)
        except Exception:
            continue
        # amounts in transactions are negative for debits; compare absolute value
        famt_abs = abs(famt)
        if any(approx_equal(famt_abs, exp) for exp in expected_amounts):
            amount_match = True
            break

if current_correct and has_completed_trip and has_wallet_txn and amount_match:
    print("SUCCESS")
else:
    print("FAILURE")
