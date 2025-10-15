import sys, json

# Strategy:
# - Load final_state_diff JSON and locate the newly added order (first entry in order.orders).
# - Verify exactly two items were ordered, both with quantity == 1.
# - Validate that one item is an apron and one is a pot using known ID sets derived from training data.
# - Confirm the pathname is the confirmation page to ensure checkout completed.
# - Print SUCCESS only if all conditions are met; otherwise print FAILURE.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_first_order(orders_dict):
    if not isinstance(orders_dict, dict) or not orders_dict:
        return None
    # Attempt to sort keys numerically when possible
    try:
        keys = sorted(orders_dict.keys(), key=lambda k: int(k))
    except Exception:
        keys = list(orders_dict.keys())
    first_key = keys[0]
    return orders_dict.get(first_key)


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        data = load_json(path)
    except Exception:
        print("FAILURE")
        return

    iff = data.get("initialfinaldiff", data)
    added = {} if not isinstance(iff, dict) else iff.get("added", {})
    updated = {} if not isinstance(iff, dict) else iff.get("updated", {})

    order_info = added.get("order", {}) if isinstance(added, dict) else {}
    orders_dict = order_info.get("orders", {}) if isinstance(order_info, dict) else {}
    order = get_first_order(orders_dict)
    if not isinstance(order, dict):
        print("FAILURE")
        return

    items = order.get("items", [])
    if not isinstance(items, list) or len(items) != 2:
        print("FAILURE")
        return

    # Known product ID sets based on training data
    apron_ids = {"226", "227", "92"}
    pot_ids = {"211", "212", "215"}

    # Validate quantities and categorize
    apron_count = 0
    pot_count = 0

    for it in items:
        if not isinstance(it, dict):
            print("FAILURE")
            return
        iid = str(it.get("id"))
        qty = it.get("quantity", 0)
        # Quantity must be exactly 1 for each item
        if not isinstance(qty, (int, float)):
            print("FAILURE")
            return
        if qty != 1:
            print("FAILURE")
            return
        if iid in apron_ids:
            apron_count += qty
        if iid in pot_ids:
            pot_count += qty

    # Must have exactly one apron and one pot
    if apron_count != 1 or pot_count != 1:
        print("FAILURE")
        return

    # Ensure we reached confirmation page
    pathname = (
        updated.get("router", {})
        .get("location", {})
        .get("pathname")
        if isinstance(updated, dict)
        else None
    )
    if pathname != "/confirmation":
        print("FAILURE")
        return

    print("SUCCESS")


if __name__ == "__main__":
    main()
