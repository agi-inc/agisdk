import json
import sys


def get_nested(d, *keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


# Compute final price given base sum, multiplier, discount


def compute_prices(base_sum, cars_cfg):
    prices = {}
    for ctype, cfg in (cars_cfg or {}).items():
        try:
            mult = float(cfg.get("multiplier", 1))
            disc = float(cfg.get("discount", 0))
            pre = base_sum * mult
            final = pre * (1 - disc)
            prices[ctype] = {
                "priceWithoutDiscount": pre,
                "finalPrice": final,
            }
        except Exception:
            continue
    return prices


# Float approx compare


def approx_equal(a, b, tol=1e-2):
    try:
        return abs(float(a) - float(b)) <= tol
    except Exception:
        return False


# Main logic:
# - Find the ride object (prefer initialfinaldiff.added.ride)
# - From ride.trips, find a completed trip with pickup name matching 'Club 26 Mix'
#   and destination name/address containing '100 Van Ness' (case-insensitive)
# - Compute cheapest car from config.udriver.cars using pickup.basePrice + destination.basePrice
# - Verify booked trip car type equals the cheapest type (allow ties within tolerance)
# - Optionally validate wallet transaction amount if present (non-fatal if missing)

try:
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)

    root = data
    ride = get_nested(root, "initialfinaldiff", "added", "ride", default=None)
    if not ride:
        # try updated section if exists
        ride = get_nested(root, "initialfinaldiff", "updated", "ride", default=None)
    if not ride or not isinstance(ride, dict):
        print("FAILURE")
        sys.exit(0)

    trips = ride.get("trips")
    if not isinstance(trips, list) or not trips:
        print("FAILURE")
        sys.exit(0)

    target_pickup = "club 26 mix"
    target_dest = "100 van ness"

    def matches_trip(t):
        try:
            if t.get("status", "").lower() != "completed":
                return False
            pu_name = (get_nested(t, "pickup", "name") or "").lower()
            dest_name = (get_nested(t, "destination", "name") or "").lower()
            dest_addr = (get_nested(t, "destination", "formattedAddress") or "").lower()
            dest_addr2 = (get_nested(t, "destination", "address") or "").lower()
            return (target_pickup in pu_name) and (
                (target_dest in dest_name)
                or (target_dest in dest_addr)
                or (target_dest in dest_addr2)
            )
        except Exception:
            return False

    matching_trips = [t for t in trips if matches_trip(t)]
    if not matching_trips:
        # No correct trip found
        print("FAILURE")
        sys.exit(0)

    # Choose the most recent matching trip if multiple: take the last occurrence in list
    booked = matching_trips[-1]

    # Extract base prices
    pu_bp = get_nested(booked, "pickup", "basePrice")
    de_bp = get_nested(booked, "destination", "basePrice")
    if pu_bp is None or de_bp is None:
        print("FAILURE")
        sys.exit(0)
    try:
        base_sum = float(pu_bp) + float(de_bp)
    except Exception:
        print("FAILURE")
        sys.exit(0)

    # Get cars config
    cars_cfg = get_nested(
        root, "initialfinaldiff", "added", "config", "udriver", "cars", default=None
    )
    if not cars_cfg:
        cars_cfg = get_nested(
            root,
            "initialfinaldiff",
            "updated",
            "config",
            "udriver",
            "cars",
            default=None,
        )
    if not isinstance(cars_cfg, dict) or not cars_cfg:
        print("FAILURE")
        sys.exit(0)

    price_map = compute_prices(base_sum, cars_cfg)
    if not price_map:
        print("FAILURE")
        sys.exit(0)

    # Identify cheapest types (account for ties within 1 cent)
    min_final = min(v["finalPrice"] for v in price_map.values())
    cheapest_types = [
        k
        for k, v in price_map.items()
        if approx_equal(v["finalPrice"], min_final, tol=1e-2) or v["finalPrice"] <= min_final + 1e-2
    ]

    booked_car = booked.get("car") or {}
    booked_type = (booked_car.get("type") or "").strip()
    booked_final = booked_car.get("finalPrice")
    booked_pre = booked_car.get("priceWithoutDiscount")

    if not booked_type or booked_type not in price_map:
        print("FAILURE")
        sys.exit(0)

    # Validate the booked price aligns with computed
    comp = price_map[booked_type]
    price_ok = True
    if booked_pre is not None:
        price_ok = price_ok and approx_equal(booked_pre, comp["priceWithoutDiscount"], tol=0.02)
    if booked_final is not None:
        price_ok = price_ok and approx_equal(booked_final, comp["finalPrice"], tol=0.02)

    if (booked_type in cheapest_types) and price_ok:
        # Optional wallet transaction check
        user = get_nested(root, "initialfinaldiff", "added", "user", default={}) or {}
        transactions = get_nested(user, "wallet", "transactions", default=[])
        if isinstance(transactions, list) and transactions:
            # Look for transaction to 100 Van Ness with amount ~ -booked_final
            desc_ok = False
            amt_ok = False
            for tx in transactions:
                desc = (tx.get("description") or "").lower()
                amt = tx.get("amount")
                if "trip to" in desc and "100 van ness" in desc:
                    desc_ok = True
                    if booked_final is not None and amt is not None:
                        if approx_equal(float(amt), -float(comp["finalPrice"]), tol=0.05):
                            amt_ok = True
                            break
            # If description match exists but amount mismatched, fail; if no such description exists, don't hard fail
            if desc_ok and not amt_ok:
                print("FAILURE")
                sys.exit(0)
        print("SUCCESS")
    else:
        print("FAILURE")
except Exception:
    # On any unexpected error, mark as failure
    print("FAILURE")
