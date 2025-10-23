import json, sys

# Strategy:
# - Confirm an order was placed by checking for 'order.orders' in the 'added' (and fallback 'updated') section.
# - Validate that at least one ordered item's product ID corresponds to a cooking pot (known IDs from catalog: 212, 215).
# - Print SUCCESS only if both conditions hold; otherwise, print FAILURE.


def get_nested(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        if k not in cur:
            return None
        cur = cur[k]
    return cur


def extract_orders(data):
    orders = []
    # Search both 'added' and 'updated' to be robust, though typically it's in 'added'
    for section in ('added', 'updated'):
        container = get_nested(data, 'initialfinaldiff', section, 'order', 'orders')
        if isinstance(container, dict):
            for _, order in container.items():
                if isinstance(order, dict):
                    orders.append(order)
    return orders


def collect_item_ids(orders):
    ids = []
    for order in orders:
        items = order.get('items')
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    _id = it.get('id')
                    if _id is not None:
                        ids.append(str(_id))
    return ids


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    orders = extract_orders(data)
    if not orders:
        # No order was placed
        print('FAILURE')
        return

    item_ids = collect_item_ids(orders)

    # Known cooking pot product IDs in Omnizon catalog observed for this task
    cooking_pot_ids = {"212", "215"}

    is_pot_ordered = any(iid in cooking_pot_ids for iid in item_ids)

    if is_pot_ordered:
        print('SUCCESS')
    else:
        print('FAILURE')


if __name__ == '__main__':
    main()