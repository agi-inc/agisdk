import json, sys

# Verification script for task: Order exactly one neck pillow
# Strategy:
# - Confirm an order exists in final state (prefer sections under initialfinaldiff.added/updated).
# - Validate that the order contains exactly one unit (total quantity == 1) and that item id is a neck pillow (IDs observed: 167 or 170).
# - Any deviation (no order, multiple items, quantity != 1, or non-neck-pillow item) => FAILURE.


def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def collect_orders(data):
    orders_list = []
    # Check both 'added' and 'updated' sections for robustness
    for section in ('added', 'updated'):
        orders = safe_get(data, ['initialfinaldiff', section, 'order', 'orders'])
        if isinstance(orders, dict) and orders:
            orders_list.append(orders)
    return orders_list


def is_valid_neck_pillow_order(order_obj):
    # Allowed neck pillow product IDs observed in training data
    allowed_ids = {"167", "170"}
    items = order_obj.get('items')
    if not isinstance(items, list) or not items:
        return False
    total_qty = 0
    allowed_qty = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        qty = it.get('quantity', 1)
        # Ensure numeric quantity
        try:
            q = int(qty)
        except Exception:
            return False
        total_qty += q
        item_id = str(it.get('id')) if 'id' in it else None
        if item_id in allowed_ids:
            allowed_qty += q
    # Exactly one unit ordered and it's a neck pillow
    return total_qty == 1 and allowed_qty == 1


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

    orders_collections = collect_orders(data)
    if not orders_collections:
        print("FAILURE")
        return

    # Validate any order entry satisfies the success criteria
    for orders in orders_collections:
        for _, order_obj in orders.items():
            if isinstance(order_obj, dict) and is_valid_neck_pillow_order(order_obj):
                print("SUCCESS")
                return

    print("FAILURE")

if __name__ == '__main__':
    main()