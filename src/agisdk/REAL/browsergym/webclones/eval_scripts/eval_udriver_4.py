import json, sys

# Verification script for: Book a ride from Aaha Indian Cuisine to Casa Loma Hotel and ensure enough credits
# Strategy:
# 1) Confirm a trip record exists in ride.trips with pickup=Aaha Indian Cuisine (id 40) and destination=Casa Loma Hotel (id 689).
# 2) Confirm credits: success if either a wallet debit transaction for this trip exists, or wallet balance >= final price and wallet is selected as payment.
# Notes: Do NOT rely on ride.trip (it may exist before booking). Only use ride.trips to confirm a booked trip.

def get_nested(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

root = data if isinstance(data, dict) else {}
added = get_nested(root, ["initialfinaldiff", "added"], {}) or {}
ride = added.get("ride", {})
user = added.get("user", {})

trips = ride.get("trips", [])

# Helper to normalize names

def norm(s):
    if s is None:
        return ""
    return str(s).strip().lower()

# Check for correct route in trips
TARGET_PICKUP_NAME = "aaha indian cuisine"
TARGET_DEST_NAME = "casa loma hotel"
TARGET_PICKUP_ID = 40
TARGET_DEST_ID = 689

matched_trip = None
for t in trips:
    pickup = t.get("pickup", {})
    dest = t.get("destination", {})
    p_name = norm(pickup.get("name"))
    d_name = norm(dest.get("name"))
    p_id = pickup.get("id")
    d_id = dest.get("id")
    status = norm(t.get("status"))
    # Require status indicates a real booking attempt
    if status not in ("in progress", "completed"):
        continue
    pickup_ok = (p_id == TARGET_PICKUP_ID) or (p_name == TARGET_PICKUP_NAME)
    dest_ok = (d_id == TARGET_DEST_ID) or (d_name == TARGET_DEST_NAME)
    if pickup_ok and dest_ok:
        matched_trip = t
        # Prefer a completed one if multiple
        if status == "completed":
            break

if not matched_trip:
    # No correct booking found
    print("FAILURE")
    sys.exit(0)

# Determine if credits condition is satisfied
wallet = user.get("wallet", {})
balance = wallet.get("balance")
try:
    balance_val = float(balance)
except Exception:
    balance_val = None

# Determine price of the matched trip
price_candidates = []
car = matched_trip.get("car", {})
if isinstance(car, dict) and isinstance(car.get("finalPrice"), (int, float)):
    price_candidates.append(float(car.get("finalPrice")))
# Fallbacks
trip_obj = ride.get("trip", {})
if isinstance(trip_obj, dict):
    car2 = trip_obj.get("car", {})
    if isinstance(car2, dict) and isinstance(car2.get("finalPrice"), (int, float)):
        price_candidates.append(float(car2.get("finalPrice")))
calc = ride.get("calculatedPrice", {})
if isinstance(calc, dict) and isinstance(calc.get("finalPrice"), (int, float)):
    price_candidates.append(float(calc.get("finalPrice")))

trip_price = price_candidates[0] if price_candidates else None

# Check payment method selection for wallet
pm_trip = matched_trip.get("paymentMethod", {}) if isinstance(matched_trip.get("paymentMethod", {}), dict) else {}
pm_sel = ride.get("selectedPaymentMethod", {}) if isinstance(ride.get("selectedPaymentMethod", {}), dict) else {}

is_wallet_trip = norm(pm_trip.get("type")) == "wallet" or ("credits" in norm(pm_trip.get("displayName")))
is_wallet_selected = norm(pm_sel.get("type")) == "wallet" or ("credits" in norm(pm_sel.get("displayName")))

# Check transactions for a debit indicating credits were used for the Casa Loma trip
transactions = wallet.get("transactions", []) if isinstance(wallet.get("transactions", []), list) else []
used_wallet_txn = False
if transactions:
    for txn in transactions:
        if not isinstance(txn, dict):
            continue
        desc = norm(txn.get("description"))
        typ = norm(txn.get("type"))
        amt = txn.get("amount")
        try:
            amt_val = float(amt)
        except Exception:
            amt_val = None
        if "trip to casa loma hotel" in desc and typ == "debit" and (amt_val is not None) and amt_val < 0:
            # Optionally validate approximate price match if price known
            if trip_price is not None:
                if abs(abs(amt_val) - trip_price) <= 0.2:
                    used_wallet_txn = True
                    break
            else:
                used_wallet_txn = True
                break

# Determine success conditions for credits
credits_ok = False
if used_wallet_txn:
    credits_ok = True
else:
    # Validate sufficient balance and wallet selection
    if (is_wallet_trip or is_wallet_selected) and (trip_price is not None) and (balance_val is not None):
        # Allow small epsilon
        if balance_val + 1e-6 >= trip_price:
            credits_ok = True

if matched_trip and credits_ok:
    print("SUCCESS")
else:
    print("FAILURE")
