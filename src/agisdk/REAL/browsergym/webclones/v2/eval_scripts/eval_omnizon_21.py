import json, sys

# Strategy:
# - Confirm an order was added with at least one item (qty >= 1) and a positive total.
# - Confirm navigation to confirmation page (router.location.pathname == "/confirmation").
# - Confirm the user context involved "bed frame" via searchInputValue or searchQuery.
# If all hold, print SUCCESS; otherwise FAILURE.

def get_in(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

initialfinaldiff = data.get("initialfinaldiff", {}) or {}
added = initialfinaldiff.get("added", {}) or {}
updated = initialfinaldiff.get("updated", {}) or {}

# Check search context contains "bed frame"
filter_updated = updated.get("filter", {}) or {}
search_vals = []
for key in ("searchInputValue", "searchQuery"):
    val = filter_updated.get(key)
    if isinstance(val, str):
        search_vals.append(val.lower())

has_bed_frame_search = any("bed frame" in v for v in search_vals)

# Check order added
orders_container = get_in(added, ["order", "orders"], default=None)
has_valid_order = False
if isinstance(orders_container, dict) and orders_container:
    for order_obj in orders_container.values():
        if not isinstance(order_obj, dict):
            continue
        items = order_obj.get("items")
        total = order_obj.get("total")
        if isinstance(items, list) and len(items) > 0:
            # Ensure at least one item has quantity >= 1
            qty_ok = any(isinstance(it, dict) and isinstance(it.get("quantity"), (int, float)) and it.get("quantity", 0) >= 1 for it in items)
            total_ok = isinstance(total, (int, float)) and total > 0
            if qty_ok and total_ok:
                has_valid_order = True
                break

# Check confirmation page
pathname = get_in(updated, ["router", "location", "pathname"], default="")
on_confirmation = isinstance(pathname, str) and pathname == "/confirmation"

if has_valid_order and on_confirmation and has_bed_frame_search:
    print("SUCCESS")
else:
    print("FAILURE")
