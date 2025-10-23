import json, sys

def norm(s):
    if s is None:
        return ""
    return str(s).strip().lower()

def get_section(data, key):
    # Prefer 'added', then 'updated'
    for sec in ("added", "updated"):
        sec_dict = data.get("initialfinaldiff", {}).get(sec, {})
        if isinstance(sec_dict, dict) and key in sec_dict and isinstance(sec_dict.get(key), dict):
            if sec_dict.get(key):
                return sec_dict.get(key)
    return {}

def approx_equal(a, b, tol=0.05):
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False

def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    ride = get_section(data, "ride")
    user = get_section(data, "user")

    # 1) Find a completed trip from Aaha Indian Cuisine to Casa Loma Hotel
    trips = ride.get("trips", []) if isinstance(ride.get("trips", []), list) else []
    target_pick = "aaha indian cuisine"
    target_dest = "casa loma hotel"

    matched_trip = None
    for t in trips:
        if norm(t.get("status")) != "completed":
            continue
        pickup_name = norm((t.get("pickup") or {}).get("name"))
        dest_name = norm((t.get("destination") or {}).get("name"))
        if target_pick in pickup_name and target_dest in dest_name:
            # Require wallet payment to satisfy "credits" condition
            pm = (t.get("paymentMethod") or {})
            if norm(pm.get("type")) == "wallet" or "credit" in norm(pm.get("displayName")):
                matched_trip = t
                break
    if not matched_trip:
        print("FAILURE")
        return

    # 2) Confirm wallet debit transaction for Casa Loma Hotel
    wallet = (user.get("wallet") or {})
    txns = wallet.get("transactions", []) if isinstance(wallet.get("transactions", []), list) else []
    debit_found = False
    txn_amount = None
    for tx in txns:
        if norm(tx.get("type")) == "debit" and target_dest in norm(tx.get("description")):
            # Should be a negative amount
            try:
                amt = float(tx.get("amount"))
            except Exception:
                continue
            if amt < 0:
                debit_found = True
                txn_amount = -amt  # make positive for comparison
                break
    if not debit_found:
        print("FAILURE")
        return

    # 3) Cross-check transaction amount roughly matches the trip price when available
    trip_price = None
    car = matched_trip.get("car") or {}
    if "finalPrice" in car:
        try:
            trip_price = float(car.get("finalPrice"))
        except Exception:
            trip_price = None
    # If we have both values, ensure they are close
    if trip_price is not None and txn_amount is not None:
        if not approx_equal(trip_price, txn_amount, tol=0.05):
            print("FAILURE")
            return

    # 4) Ensure wallet balance is non-negative (indicates sufficient credits after charge)
    balance_ok = True
    try:
        bal = float(wallet.get("balance", 0))
        if bal < -1e-6:
            balance_ok = False
    except Exception:
        # If balance missing or invalid, be conservative and fail credits condition
        balance_ok = False
    if not balance_ok:
        print("FAILURE")
        return

    print("SUCCESS")

if __name__ == "__main__":
    main()
