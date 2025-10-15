import json, sys

def get_nested(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def find_section(obj):
    # Try to locate the ride and user objects inside added/updated sections
    root = obj.get('initialfinaldiff', obj)
    candidates = []
    for key in ['added', 'updated']:
        sec = root.get(key)
        if isinstance(sec, dict):
            candidates.append(sec)
    # Also consider root directly if it already has ride/user
    if isinstance(root, dict):
        candidates.append(root)
    ride = None
    user = None
    for sec in candidates:
        if ride is None and isinstance(sec.get('ride'), dict) and sec.get('ride'):
            ride = sec.get('ride')
        if user is None and isinstance(sec.get('user'), dict) and sec.get('user'):
            user = sec.get('user')
    return ride, user

def text(s):
    if isinstance(s, str):
        return s.strip().lower()
    return ''

def match_pickup(loc):
    if not isinstance(loc, dict):
        return False
    # Multiple robust signals for Ai Electronics Center
    name = text(loc.get('name'))
    addr = text(loc.get('address'))
    faddr = text(loc.get('formattedAddress'))
    loc_id = loc.get('id')
    # Accept if id matches known id
    if loc_id == 370:
        return True
    # Accept if name contains ai + electronics center
    if ('electronics center' in name and ('ai ' in name or name.startswith('ai') or 'ai' in name)):
        return True
    # Accept if address contains the street address
    if '4790 mission' in addr or '4790 mission' in faddr:
        return True
    return False

def match_dropoff(loc):
    if not isinstance(loc, dict):
        return False
    name = text(loc.get('name'))
    addr = text(loc.get('address'))
    faddr = text(loc.get('formattedAddress'))
    loc_id = loc.get('id')
    if loc_id == 733:
        return True
    if '333 fremont apartments' in name:
        return True
    if '333 fremont st' in addr or '333 fremont st' in faddr or '333 fremont street' in addr or '333 fremont street' in faddr:
        return True
    return False

def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    ride, user = find_section(data)
    if not isinstance(ride, dict):
        print('FAILURE')
        return

    pickup_ok = match_pickup(ride.get('pickupLocation'))
    dropoff_ok = match_dropoff(ride.get('dropoffLocation'))

    # Determine if rides/prices were actually shown. Training indicates calculatedPrice.finalPrice > 0 for success
    calc = ride.get('calculatedPrice') or {}
    try:
        final_price = float(calc.get('finalPrice') or 0)
    except Exception:
        final_price = 0.0

    rides_shown = final_price > 0

    # Optional: read wallet balance to ensure the script considers credits (does not gate success)
    balance = None
    if isinstance(user, dict):
        balance = get_nested(user, ['wallet', 'balance'])
        try:
            balance = float(balance)
        except Exception:
            balance = None

    # Success criteria: correct route AND rides/prices shown
    if pickup_ok and dropoff_ok and rides_shown:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
