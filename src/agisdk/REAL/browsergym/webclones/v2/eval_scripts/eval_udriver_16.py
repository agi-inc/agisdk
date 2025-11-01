import sys, json

def norm(s):
    if s is None:
        return ""
    return str(s).strip().lower()

EXPECTED_PICKUP_NAME = "1 hotel san francisco"
EXPECTED_PICKUP_ADDR_HINT = "8 mission"
EXPECTED_DEST_NAME_CORE = "100 van ness"  # matches name and formattedAddress with Ave


def is_expected_pickup(p):
    if not isinstance(p, dict):
        return False
    name = norm(p.get("name"))
    fmt = norm(p.get("formattedAddress"))
    addr = norm(p.get("address"))
    pid = p.get("id")
    # Accept if name matches or id known constant or address hint present
    if EXPECTED_PICKUP_NAME in name:
        return True
    if pid == 699:
        return True
    if EXPECTED_PICKUP_ADDR_HINT in fmt or EXPECTED_PICKUP_ADDR_HINT in addr:
        # Also ensure city to avoid accidental matches
        if "san francisco" in fmt or "san francisco" in addr:
            return True
    return False


def is_expected_destination(d):
    if not isinstance(d, dict):
        return False
    name = norm(d.get("name"))
    fmt = norm(d.get("formattedAddress"))
    addr = norm(d.get("address"))
    did = d.get("id")
    # Accept if name contains "100 van ness" or id known constant or address contains it
    if EXPECTED_DEST_NAME_CORE in name:
        return True
    if did == 717:
        return True
    if EXPECTED_DEST_NAME_CORE in fmt or EXPECTED_DEST_NAME_CORE in addr:
        return True
    return False


def has_completed_correct_trip(ride):
    trips = []
    if isinstance(ride, dict):
        trips = ride.get("trips") or []
    if not isinstance(trips, list):
        return False
    for t in trips:
        if not isinstance(t, dict):
            continue
        status = norm(t.get("status"))
        if status != "completed":
            continue
        pickup = t.get("pickup", {})
        dest = t.get("destination", {})
        if is_expected_pickup(pickup) and is_expected_destination(dest):
            return True
    return False


def wallet_has_destination_debit(user):
    # Look for a debit (or negative amount) transaction mentioning 100 Van Ness
    if not isinstance(user, dict):
        return False
    wallet = user.get("wallet") or {}
    txs = wallet.get("transactions") or []
    if not isinstance(txs, list):
        return False
    for tx in txs:
        if not isinstance(tx, dict):
            continue
        desc = norm(tx.get("description"))
        typ = norm(tx.get("type"))
        amount = tx.get("amount")
        has_dest = EXPECTED_DEST_NAME_CORE in desc
        is_debit = (typ == "debit") or (isinstance(amount, (int, float)) and amount < 0)
        if has_dest and is_debit:
            return True
    return False


def extract_section(data, key):
    # Try to extract a section (ride/user) from added first then updated
    if not isinstance(data, dict):
        return None
    init = data.get("initialfinaldiff") or {}
    added = init.get("added") or {}
    updated = init.get("updated") or {}
    sec = None
    if isinstance(added, dict):
        sec = added.get(key)
    if sec is None and isinstance(updated, dict):
        sec = updated.get(key)
    return sec


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    ride = extract_section(data, "ride") or {}
    user = extract_section(data, "user") or {}

    # Strategy: require both a completed trip with correct direction and a matching wallet debit to 100 Van Ness.
    ok_trip = has_completed_correct_trip(ride)
    ok_wallet = wallet_has_destination_debit(user)

    if ok_trip and ok_wallet:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()