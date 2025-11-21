import json
import sys


def get_nested(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


# Strategy in code comments:
# - Verify the task by confirming an actual placed order contains the target item.
# - Search cartItems only within foodOrders (placed orders) found under differences.foodOrders.added and initialfinaldiff.added.cart.foodOrders.
# - Match item if name includes 'lemon pepper' and 'wing' and restaurant contains 'wingstop' (all case-insensitive).

try:
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

items = []

# Collect from differences.foodOrders.added
added_orders = get_nested(data, ["differences", "foodOrders", "added"], {})
if isinstance(added_orders, dict):
    for _, order in added_orders.items():
        if isinstance(order, dict):
            cart_items = order.get("cartItems", [])
            if isinstance(cart_items, list):
                items.extend(cart_items)

# Collect from initialfinaldiff.added.cart.foodOrders
init_orders = get_nested(data, ["initialfinaldiff", "added", "cart", "foodOrders"], {})
if isinstance(init_orders, dict):
    for _, order in init_orders.items():
        if isinstance(order, dict):
            cart_items = order.get("cartItems", [])
            if isinstance(cart_items, list):
                items.extend(cart_items)

# Determine if any placed order item matches the target criteria
success = False
for it in items:
    if not isinstance(it, dict):
        continue
    name = str(it.get("name", "")).strip().lower()
    restaurant = str(it.get("restaurantName", "")).strip().lower()
    if ("lemon" in name and "pepper" in name and "wing" in name) and ("wingstop" in restaurant):
        qty = it.get("quantity", 1)
        try:
            qty_val = int(qty)
        except Exception:
            qty_val = 1 if qty else 0
        if qty_val > 0:
            success = True
            break

print("SUCCESS" if success else "FAILURE")
