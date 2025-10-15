import json, sys

# Strategy:
# 1) Confirm a purchase was completed by checking for a confirmation route and an added order with items.
# 2) Validate the purchased item is a toy within $15-$50 by requiring:
#    - User searched for 'toy' (case-insensitive) and
#    - Heuristic: toy item IDs are under 200
#    - Price within [15, 50]
# If any of these checks fail, output FAILURE; else SUCCESS.

def get_nested(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


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

    initdiff = data.get("initialfinaldiff")
    if not isinstance(initdiff, dict):
        print("FAILURE")
        return

    # Check we navigated to confirmation page (purchase flow completed)
    pathname = get_nested(initdiff, ["updated", "router", "location", "pathname"]) or ""
    if "/confirmation" not in str(pathname):
        print("FAILURE")
        return

    orders_obj = get_nested(initdiff, ["added", "order", "orders"], {})
    if not isinstance(orders_obj, dict) or not orders_obj:
        # No orders recorded
        print("FAILURE")
        return

    # Extract all items from all orders
    items = []
    for _, order in orders_obj.items():
        its = []
        try:
            its = order.get("items", [])
        except Exception:
            its = []
        if isinstance(its, list):
            items.extend(its)

    if not items:
        print("FAILURE")
        return

    # Check that user intent was to buy a toy
    search_q = get_nested(initdiff, ["updated", "filter", "searchQuery"]) or ""
    search_in = get_nested(initdiff, ["updated", "filter", "searchInputValue"]) or ""
    searched_toy = (isinstance(search_q, str) and "toy" in search_q.lower()) or (isinstance(search_in, str) and "toy" in search_in.lower())

    # Determine if any purchased item satisfies toy + price constraints
    success = False
    for it in items:
        price = it.get("price")
        id_str = it.get("id")
        # Parse id to int if possible for heuristic
        id_int = None
        try:
            if isinstance(id_str, int):
                id_int = id_str
            elif isinstance(id_str, str) and id_str.isdigit():
                id_int = int(id_str)
        except Exception:
            id_int = None

        # Heuristic: toy IDs are under 200
        id_looks_toy = (id_int is not None and id_int < 200)

        price_ok = False
        try:
            if isinstance(price, (int, float)):
                price_ok = (price >= 15 and price <= 50)
        except Exception:
            price_ok = False

        if searched_toy and id_looks_toy and price_ok:
            success = True
            break

    print("SUCCESS" if success else "FAILURE")

if __name__ == "__main__":
    main()
