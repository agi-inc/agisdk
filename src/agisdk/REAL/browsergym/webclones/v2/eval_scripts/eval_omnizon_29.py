import json, sys


# - Confirm exactly two items were ordered, each with quantity 1
# - Require that one of the items is the 40-inch desk with id "159"


def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def pick_latest_order(orders_dict):
    # orders_dict is a dict of index->orderObj
    if not isinstance(orders_dict, dict) or not orders_dict:
        return None
    # Prefer max date if available; fall back to highest orderNumber; else last by key
    def order_sort_key(o):
        date = o.get('date')
        order_num = o.get('orderNumber')
        return (
            1 if isinstance(date, str) else 0,
            date if isinstance(date, str) else '',
            str(order_num) if order_num is not None else ''
        )
    # Choose the max by the tuple key
    latest = None
    for k, v in orders_dict.items():
        if not isinstance(v, dict):
            continue
        if latest is None or order_sort_key(v) > order_sort_key(latest):
            latest = v
    return latest


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    orders = safe_get(data, ['initialfinaldiff', 'added', 'order', 'orders'])
    order_obj = pick_latest_order(orders)
    if not isinstance(order_obj, dict):
        # No order placed
        print("FAILURE")
        return

    items = order_obj.get('items', [])
    if not isinstance(items, list) or len(items) != 2:
        print("FAILURE")
        return

    # Normalize items to ensure id is string and quantity as int (default 1)
    norm_items = []
    for it in items:
        if not isinstance(it, dict):
            continue
        iid = str(it.get('id')) if 'id' in it else None
        qty_raw = it.get('quantity', 1)
        try:
            qty = int(qty_raw)
        except Exception:
            try:
                qty = int(float(qty_raw))
            except Exception:
                qty = 0
        norm_items.append((iid, qty))

    # Must still have two normalized items
    if len(norm_items) != 2:
        print("FAILURE")
        return

    # Conditions: exactly two items, each qty == 1
    if not all(q == 1 for _, q in norm_items):
        print("FAILURE")
        return

    # Must include the 40-inch desk id '159' exactly once
    desk_count = sum(1 for iid, q in norm_items if iid == '159' and q == 1)
    if desk_count != 1:
        print("FAILURE")
        return

    # Passed all checks
    print("SUCCESS")


if __name__ == '__main__':
    main()