import sys, json, re

# Strategy:
# 1) Confirm correct route: pickup = Ai Electronics Center.Com (RF1, id 370) and dropoff = 333 Fremont Apartments (DLO, id 733), in that order.
# 2) Ensure rides were shown by requiring calculatedPrice.finalPrice > 0.
# 3) Ensure wallet balance exists to allow checking if credits are enough (not requiring sufficiency, just availability to check).
# If all conditions hold, print SUCCESS; else FAILURE.

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

def get_section(data, *keys):
    cur = data
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur

def norm_text(s):
    if not isinstance(s, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def is_ai_electronics(loc):
    if not isinstance(loc, dict):
        return False
    # Prefer stable identifiers/ids if present
    if loc.get('id') == 370 or loc.get('identifier') == 'RF1':
        return True
    name = norm_text(loc.get('name', ''))
    addr = norm_text(loc.get('address', ''))
    return ('aielectronics' in name) or ('aielectronics' in addr) or ('aielectronicscentercom' in name)

def is_333_fremont(loc):
    if not isinstance(loc, dict):
        return False
    if loc.get('id') == 733 or loc.get('identifier') == 'DLO':
        return True
    name = norm_text(loc.get('name', ''))
    addr = norm_text(loc.get('address', ''))
    return ('333fremont' in name) or ('333fremont' in addr)


def main():
    path = sys.argv[1]
    data = load_json(path)

    # Navigate to the diff structure, prefer 'added', fallback to 'updated', then root.
    root = data.get('initialfinaldiff', {})
    added = root.get('added', {}) if isinstance(root, dict) else {}
    updated = root.get('updated', {}) if isinstance(root, dict) else {}

    ride = added.get('ride') or updated.get('ride') or data.get('ride') or {}
    user = added.get('user') or updated.get('user') or data.get('user') or {}

    pickup = ride.get('pickupLocation') or {}
    dropoff = ride.get('dropoffLocation') or {}

    pickup_ok = is_ai_electronics(pickup)
    dropoff_ok = is_333_fremont(dropoff)

    # Must be correct direction
    route_ok = pickup_ok and dropoff_ok

    # Ensure rides/prices were actually shown: calculatedPrice.finalPrice > 0
    calc_price = None
    cp = ride.get('calculatedPrice')
    if isinstance(cp, dict):
        fp = cp.get('finalPrice')
        if isinstance(fp, (int, float)):
            calc_price = float(fp)
    price_ok = (calc_price is not None) and (calc_price > 0)

    # Require wallet balance present to allow credits check
    wallet = get_section(user, 'wallet') or {}
    balance = wallet.get('balance')
    balance_ok = isinstance(balance, (int, float))

    # Overall success determination
    if route_ok and price_ok and balance_ok:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
