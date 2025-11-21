import json
import sys


def get_nested(d, *keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def text_contains(text, needle):
    if not isinstance(text, str):
        return False
    return needle.lower() in text.lower()


def any_contains(values, needle):
    for v in values:
        if text_contains(v, needle):
            return True
    return False


def is_pickup_388_beale(loc):
    if not isinstance(loc, dict):
        return False
    # Prefer stable ID when available
    if loc.get("id") == 739:
        return True
    # Fallback to name/address match
    name = loc.get("name")
    addr = loc.get("address")
    faddr = loc.get("formattedAddress")
    comps = (
        loc.get("addressComponents", {}) if isinstance(loc.get("addressComponents"), dict) else {}
    )
    street = comps.get("street") if isinstance(comps, dict) else None
    return any_contains([name, addr, faddr, street], "388 Beale")


def is_dest_amber_india(loc):
    if not isinstance(loc, dict):
        return False
    # Prefer stable ID when available
    if loc.get("id") == 52:
        return True
    # Fallback to name/address match (allow partial 'Amber India')
    name = loc.get("name")
    addr = loc.get("address")
    faddr = loc.get("formattedAddress")
    comps = (
        loc.get("addressComponents", {}) if isinstance(loc.get("addressComponents"), dict) else {}
    )
    street = comps.get("street") if isinstance(comps, dict) else None
    return any_contains([name, addr, faddr, street], "Amber India")


def has_wallet_tx_to_amber(user, expected_amount=None):
    if not isinstance(user, dict):
        return False
    wallet = user.get("wallet")
    if not isinstance(wallet, dict):
        return False
    txs = wallet.get("transactions")
    if not isinstance(txs, list):
        return False
    found = False
    for tx in txs:
        if not isinstance(tx, dict):
            continue
        desc = tx.get("description", "")
        amt = tx.get("amount")
        ttype = tx.get("type")
        # Must be a debit and mention Amber India
        if ttype == "debit" and any_contains([desc], "Amber India"):
            if expected_amount is None:
                found = True
                break
            # Allow small float tolerance
            try:
                if isinstance(amt, (int, float)) and expected_amount is not None:
                    if abs(float(amt) - float(expected_amount)) < 1e-6:
                        found = True
                        break
            except Exception:
                pass
    return found


def main():
    try:
        path = sys.argv[1]
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Support multiple possible roots
    root = data.get("initialfinaldiff") if isinstance(data, dict) else None
    if not isinstance(root, dict):
        root = data.get("final_state_diff", {}) if isinstance(data, dict) else {}
    added = root.get("added", {}) if isinstance(root, dict) else {}

    ride = added.get("ride", {}) if isinstance(added, dict) else {}
    user = added.get("user", {}) if isinstance(added, dict) else {}

    trip = ride.get("trip") if isinstance(ride, dict) else None
    if not isinstance(trip, dict):
        print("FAILURE")
        return

    pickup = trip.get("pickup")
    dest = trip.get("destination")
    car = trip.get("car", {}) if isinstance(trip, dict) else {}

    # Validate pickup and destination exactly as requested (not flipped)
    pickup_ok = is_pickup_388_beale(pickup)
    dest_ok = is_dest_amber_india(dest)

    # Validate vehicle type is XL
    car_type = (car.get("type") or "") if isinstance(car, dict) else ""
    car_ok = isinstance(car_type, str) and car_type.lower() == "udriverxl"

    # Optional: validate transaction shows booking to Amber India
    if isinstance(car, dict) and isinstance(car.get("finalPrice"), (int, float)):
        car.get("finalPrice")

    wallet_ok = has_wallet_tx_to_amber(user, expected_amount=None)

    if pickup_ok and dest_ok and car_ok and wallet_ok:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
