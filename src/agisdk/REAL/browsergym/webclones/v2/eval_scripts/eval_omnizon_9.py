import json
import sys

# Verification script for: Omnizon - Order me a desk chair for my new desk
# Strategy:
# 1) Confirm an order exists in initialfinaldiff.added.order.orders (indicates a placed order).
# 2) Validate that at least one ordered item corresponds to a desk chair by checking known product IDs {122, 123}.
#    If a qualifying item is found, print SUCCESS; else FAILURE.

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def iter_orders(orders_node):
    if orders_node is None:
        return []
    if isinstance(orders_node, dict):
        return list(orders_node.values())
    if isinstance(orders_node, list):
        return list(orders_node)
    return []


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

    diff = data.get('initialfinaldiff') or {}
    if not isinstance(diff, dict):
        print("FAILURE")
        return

    added = diff.get('added') or {}
    if not isinstance(added, dict):
        print("FAILURE")
        return

    order_section = added.get('order') or {}
    if not isinstance(order_section, dict):
        print("FAILURE")
        return

    orders_node = order_section.get('orders')
    orders = iter_orders(orders_node)

    # Known desk chair product IDs (from successful examples)
    desk_chair_ids = {"122", "123"}

    placed_chair_order = False

    for order_obj in orders:
        if not isinstance(order_obj, dict):
            continue
        items = order_obj.get('items') or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get('id')
            if item_id is None:
                continue
            item_id_str = str(item_id)
            quantity = item.get('quantity', 0)
            try:
                qty_int = int(quantity)
            except Exception:
                # If quantity isn't an int, treat as non-positive
                qty_int = 0
            if item_id_str in desk_chair_ids and qty_int > 0:
                placed_chair_order = True
                break
        if placed_chair_order:
            break

    print("SUCCESS" if placed_chair_order else "FAILURE")

if __name__ == "__main__":
    main()
