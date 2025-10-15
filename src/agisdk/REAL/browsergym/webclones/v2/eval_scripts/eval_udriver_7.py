import json, sys

def get_in(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    added = get_in(data, ['initialfinaldiff', 'added'], {}) or {}
    ride = added.get('ride', {}) or {}
    user = added.get('user', {}) or {}
    config = added.get('config', {}) or {}

    booked = ride.get('bookedTrip')

    # Must have a scheduled booking
    if not booked:
        print('FAILURE')
        sys.exit(0)

    # Validate time is 7:00 PM
    time_str = (booked.get('time') or '').strip()
    if time_str != '7:00 PM':
        print('FAILURE')
        sys.exit(0)

    # Validate pickup and dropoff are correct for the booking
    pickup = booked.get('pickup') or {}
    dest = booked.get('destination') or {}
    pickup_name = (pickup.get('name') or '').strip().lower()
    dest_name = (dest.get('name') or '').strip().lower()
    pickup_id = pickup.get('id')
    dest_id = dest.get('id')

    pickup_ok = (pickup_id == 715) or (pickup_name == '77 bluxome apartments')
    dest_ok = (dest_id == 207) or (dest_name == 'audio nightclub')
    if not (pickup_ok and dest_ok):
        print('FAILURE')
        sys.exit(0)

    # Validate date corresponds to the selected date ("tonight") if available
    booked_date = (booked.get('date') or '').strip()
    ride_pickup_date = (ride.get('pickupDate') or '').strip()
    if not booked_date:
        # Must have a concrete date
        print('FAILURE')
        sys.exit(0)
    if ride_pickup_date and (booked_date != ride_pickup_date):
        print('FAILURE')
        sys.exit(0)

    # If user has enough credits, the booked car must be UdriverXL
    # Compute XL price from base prices and config multipliers/discounts
    base_sum = 0.0
    try:
        base_sum = float(pickup.get('basePrice', 0)) + float(dest.get('basePrice', 0))
    except Exception:
        base_sum = 0.0

    cars_cfg = get_in(config, ['udriver', 'cars'], {}) or {}
    xl_cfg = cars_cfg.get('UdriverXL', {}) if isinstance(cars_cfg, dict) else {}
    xl_multiplier = xl_cfg.get('multiplier', 1)
    xl_discount = xl_cfg.get('discount', 0)
    try:
        xl_multiplier = float(xl_multiplier)
    except Exception:
        xl_multiplier = 1.0
    try:
        xl_discount = float(xl_discount)
    except Exception:
        xl_discount = 0.0

    price_without = base_sum * xl_multiplier
    xl_final_price = round(price_without * (1 - xl_discount), 2)

    wallet_balance = get_in(user, ['wallet', 'balance'], 0) or 0
    try:
        wallet_balance = float(wallet_balance)
    except Exception:
        wallet_balance = 0.0

    booked_car = (get_in(booked, ['car', 'type']) or '').strip()

    # If enough credits, enforce XL booking
    if wallet_balance + 1e-6 >= xl_final_price - 1e-6:
        if booked_car != 'UdriverXL':
            print('FAILURE')
            sys.exit(0)

    # All checks passed
    print('SUCCESS')
except Exception:
    # Any unexpected issue -> fail conservatively
    print('FAILURE')
