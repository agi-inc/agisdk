import json, sys

def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur

# Strategy in code comments:
# 1) Verify an order exists and the app navigated to the confirmation page.
# 2) Validate the order contains a gaming laptop under $1000 and a monitor.
#    From training data: gaming laptop id = '201'; monitor ids = {'10', '125', '127'}.
#    Accept any quantities >= 1 and ensure price constraint on the gaming laptop.

def extract_orders(data):
    orders = []
    # Look into both 'added' and 'updated' just in case
    for section in ("added", "updated"):
        orders_dict = safe_get(data, ["initialfinaldiff", section, "order", "orders"], {})
        if isinstance(orders_dict, dict):
            for _, order in orders_dict.items():
                if isinstance(order, dict):
                    items = order.get("items")
                    if isinstance(items, list) and items:
                        orders.append(order)
    return orders


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

    # Check confirmation page
    pathname = None
    for section in ("updated", "added"):
        p = safe_get(data, ["initialfinaldiff", section, "router", "location", "pathname"])
        if p:
            pathname = p
            break

    orders = extract_orders(data)

    if not orders or pathname != "/confirmation":
        print("FAILURE")
        return

    # Define product mappings inferred from training data
    GAMING_LAPTOP_IDS = {"201"}
    MONITOR_IDS = {"10", "125", "127"}

    has_gaming_laptop = False
    has_monitor = False

    # Iterate through all orders (usually one) and all items
    for order in orders:
        items = order.get("items", [])
        for it in items:
            if not isinstance(it, dict):
                continue
            item_id = str(it.get("id"))
            qty = it.get("quantity", 0) or 0
            price = it.get("price")
            # Ensure price is numeric when needed
            try:
                price_val = float(price) if price is not None else None
            except Exception:
                price_val = None

            if item_id in GAMING_LAPTOP_IDS and qty >= 1:
                if price_val is not None and price_val <= 1000.0:
                    has_gaming_laptop = True
            if item_id in MONITOR_IDS and qty >= 1:
                has_monitor = True

    if has_gaming_laptop and has_monitor:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
