import json
import sys

# Strategy:
# 1) Confirm an order was actually placed by finding entries in foodOrders (not just items in cart).
# 2) For each placed order, check that at least one cart item is a sandwich/sub (name contains 'sandwich' or 'sub').
# 3) Verify the order's totalAmount (including fees/tip) is strictly less than 25.
# If any order satisfies both conditions, print SUCCESS; else FAILURE.


def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def collect_orders(data):
    orders = []
    # Primary path seen in examples
    fo_map = safe_get(data, ["initialfinaldiff", "added", "cart", "foodOrders"], {})
    if isinstance(fo_map, dict):
        for v in fo_map.values():
            if isinstance(v, dict):
                orders.append(v)
    # Fallback via differences
    diff_added = safe_get(data, ["differences", "foodOrders", "added"], {})
    if isinstance(diff_added, dict):
        for v in diff_added.values():
            if isinstance(v, dict):
                orders.append(v)
    return orders


def is_sandwich_item(name: str) -> bool:
    if not isinstance(name, str):
        return False
    n = name.lower()
    # Consider 'sandwich' or 'sub' as sandwich indicators.
    return ("sandwich" in n) or ("sub" in n)


def parse_float(x):
    try:
        return float(x)
    except Exception:
        return None


def evaluate(data):
    orders = collect_orders(data)
    if not orders:
        return False
    for order in orders:
        charges = order.get("checkoutDetails", {}).get("charges", {})
        total = parse_float(charges.get("totalAmount"))
        if total is None:
            continue
        if total >= 25:
            continue
        items = order.get("cartItems", [])
        has_sandwich = any(is_sandwich_item(it.get("name")) for it in items if isinstance(it, dict))
        if has_sandwich:
            return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return
    ok = evaluate(data)
    print("SUCCESS" if ok else "FAILURE")


if __name__ == "__main__":
    main()
