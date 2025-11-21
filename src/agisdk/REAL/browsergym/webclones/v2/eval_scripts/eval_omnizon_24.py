import json
import sys

# - Validate that the order items are exclusively PS5 controllers (id "16") and total ordered quantity equals 2.


def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


try:
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)

    root = data if isinstance(data, dict) else {}

    # Check we've reached confirmation page
    pathname = safe_get(root, ["initialfinaldiff", "updated", "router", "location", "pathname"], "")
    on_confirmation = pathname == "/confirmation"

    # Extract orders dict
    orders = safe_get(root, ["initialfinaldiff", "added", "order", "orders"], {})
    success_order_found = False

    if isinstance(orders, dict):
        for _, order in orders.items():
            items = order.get("items", []) if isinstance(order, dict) else []
            if not isinstance(items, list) or not items:
                continue
            # All items must be PS5 controller id "16"
            all_16 = True
            qty_16 = 0
            for it in items:
                if not isinstance(it, dict):
                    all_16 = False
                    break
                item_id = str(it.get("id"))
                qty = it.get("quantity", 0)
                if item_id != "16":
                    all_16 = False
                    break
                # Guard non-int quantities
                try:
                    qty_val = int(qty)
                except Exception:
                    qty_val = 0
                qty_16 += qty_val
            if all_16 and qty_16 == 2:
                success_order_found = True
                break

    if on_confirmation and success_order_found:
        print("SUCCESS")
    else:
        print("FAILURE")
except Exception:
    # Any parsing/runtime error -> fail safe
    print("FAILURE")
