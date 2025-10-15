import json, sys

def get_path(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

# Strategy in code:
# 1) Confirm a purchase flow completed by checking router.location.pathname == "/confirmation" and that an order was added.
# 2) Verify at least one ordered item has a price under $40 and plausibly is a kit (heuristic: price >= $8 to avoid single cheap items), and avoid known invalid state (popup removal flag).
# 3) Be robust to missing fields and multiple orders/items; any qualifying item yields success.

def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diff = data.get('initialfinaldiff')
    if not isinstance(diff, dict):
        print("FAILURE")
        return

    # If a specific config flag indicates popup removal (seen in a failed case), treat as failure
    remove_popup = get_path(diff, ['updated', 'config', 'omnizon', 'removePopup'], False)
    if remove_popup is True:
        print("FAILURE")
        return

    # Ensure navigation reached confirmation page
    pathname = get_path(diff, ['updated', 'router', 'location', 'pathname'])
    if pathname != '/confirmation':
        # Some successful cases might store pathname under added? Typically it's under updated; if missing, fail
        print("FAILURE")
        return

    orders = get_path(diff, ['added', 'order', 'orders'])
    if not isinstance(orders, dict) or not orders:
        print("FAILURE")
        return

    # Look for any item within any order that qualifies: price between [8, 40]
    found_qualifying_item = False
    for _, order in orders.items():
        items = order.get('items') if isinstance(order, dict) else None
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            price = item.get('price')
            try:
                price_val = float(price)
            except (TypeError, ValueError):
                continue
            # Must be under or equal to 40 (budget) and above a minimal price to better indicate a kit rather than a single ultra-cheap item
            if 8.0 <= price_val <= 40.0:
                found_qualifying_item = True
                break
        if found_qualifying_item:
            break

    if found_qualifying_item:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
