import json, sys

# Strategy:
# 1) Confirm an actual order exists by collecting orders from both initialfinaldiff.added.cart.foodOrders
#    and differences.foodOrders.added.
# 2) For each order, check if any cart item name contains 'rotisserie', 'chicken', and 'sandwich' (case-insensitive),
#    and that the order's checkoutDetails.charges.totalAmount < 30. If such an order exists, print SUCCESS; else FAILURE.

def to_float(val):
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            return float(val.strip().replace('$',''))
    except Exception:
        return None
    return None


def extract_orders(data):
    orders = []
    seen_ids = set()
    # From initialfinaldiff
    fi = data.get("initialfinaldiff", {}).get("added", {}).get("cart", {}).get("foodOrders", {})
    if isinstance(fi, dict):
        for k, v in fi.items():
            if isinstance(v, dict):
                oid = v.get('orderId') or f"init_{k}"
                if oid not in seen_ids:
                    orders.append(v)
                    seen_ids.add(oid)
    # From differences
    fd = data.get("differences", {}).get("foodOrders", {}).get("added", {})
    if isinstance(fd, dict):
        for k, v in fd.items():
            if isinstance(v, dict):
                oid = v.get('orderId') or f"diff_{k}"
                if oid not in seen_ids:
                    orders.append(v)
                    seen_ids.add(oid)
    return orders


def item_matches(name):
    if not name:
        return False
    n = str(name).lower()
    return ('rotisserie' in n) and ('chicken' in n) and ('sandwich' in n)


def verify(data):
    orders = extract_orders(data)
    if not orders:
        return False
    # Check each order for matching item and price constraint
    for order in orders:
        cart_items = order.get('cartItems') or []
        if not isinstance(cart_items, list):
            continue
        has_target_item = any(item_matches(ci.get('name')) for ci in cart_items if isinstance(ci, dict))
        if not has_target_item:
            continue
        charges = (order.get('checkoutDetails') or {}).get('charges') or {}
        total = to_float(charges.get('totalAmount'))
        if total is None:
            continue
        if total < 30.0:
            return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return
    print("SUCCESS" if verify(data) else "FAILURE")

if __name__ == '__main__':
    main()