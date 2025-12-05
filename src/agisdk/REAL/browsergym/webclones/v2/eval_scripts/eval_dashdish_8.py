import json
import sys

# Verifier for: Order $20 worth of food from Taco Boys
# Strategy:
# 1) Extract all placed orders from both initialfinaldiff.added.cart.foodOrders and differences.foodOrders.added.
# 2) For each order, check if any cart item is from "Taco Boys" (case-insensitive) and if charges.totalAmount >= 20.
# 3) If any order satisfies both conditions, print SUCCESS; else, FAILURE.


def safe_get(d, *keys):
    for k in keys:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return None
    return d


def extract_orders(state):
    orders = []
    seen_ids = set()

    # From initialfinaldiff.added.cart.foodOrders
    fod = safe_get(state, "initialfinaldiff", "added", "cart", "foodOrders")
    if isinstance(fod, dict):
        for _, od in fod.items():
            if isinstance(od, dict):
                oid = od.get("orderId")
                if oid not in seen_ids:
                    seen_ids.add(oid)
                    orders.append(od)

    # From differences.foodOrders.added
    diff_added = safe_get(state, "differences", "foodOrders", "added")
    if isinstance(diff_added, dict):
        for _, od in diff_added.items():
            if isinstance(od, dict):
                oid = od.get("orderId")
                if oid not in seen_ids:
                    seen_ids.add(oid)
                    orders.append(od)

    return orders


def is_taco_boys_item(item):
    if not isinstance(item, dict):
        return False
    rn = item.get("restaurantName")
    if not isinstance(rn, str):
        return False
    return "taco boys" in rn.strip().lower()


def parse_total_amount(order):
    charges = safe_get(order, "checkoutDetails", "charges")
    if isinstance(charges, dict):
        ta = charges.get("totalAmount")
        if isinstance(ta, (int, float)):
            return float(ta)
        # Handle string numeric just in case
        if isinstance(ta, str):
            try:
                return float(ta.replace("$", "").strip())
            except:
                return 0.0
    return 0.0


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return

    try:
        with open(path) as f:
            state = json.load(f)
    except Exception:
        print("FAILURE")
        return

    orders = extract_orders(state)

    success = False
    for od in orders:
        items = od.get("cartItems")
        if not isinstance(items, list) or len(items) == 0:
            continue
        has_taco = any(is_taco_boys_item(it) for it in items)
        total_amt = parse_total_amount(od)
        if has_taco and total_amt >= 20.0:
            success = True
            break

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
