import json, sys

def get_pathname(data):
    # Try common locations
    try:
        return data.get('initialfinaldiff', {}).get('updated', {}).get('router', {}).get('location', {}).get('pathname')
    except Exception:
        pass
    try:
        return data.get('initialfinaldiff', {}).get('added', {}).get('router', {}).get('location', {}).get('pathname')
    except Exception:
        pass
    # Fallback: shallow search for pathname under router/location in both sections
    for section in ('updated', 'added'):
        sec = data.get('initialfinaldiff', {}).get(section, {})
        if isinstance(sec, dict):
            router = sec.get('router', {})
            if isinstance(router, dict):
                loc = router.get('location', {})
                if isinstance(loc, dict):
                    pn = loc.get('pathname')
                    if pn is not None:
                        return pn
    return None


def get_order_items(data):
    # Search in 'added' then 'updated' for order->orders
    base = data.get('initialfinaldiff', {})
    for section in ('added', 'updated'):
        sec = base.get(section, {})
        if not isinstance(sec, dict):
            continue
        order = sec.get('order', {})
        if not isinstance(order, dict):
            continue
        orders_map = order.get('orders')
        if isinstance(orders_map, dict) and orders_map:
            # choose the first order by sorted key to be deterministic
            try:
                keys = sorted(orders_map.keys(), key=lambda x: str(x))
            except Exception:
                keys = list(orders_map.keys())
            first = orders_map.get(keys[0])
            if isinstance(first, dict):
                items = first.get('items')
                if isinstance(items, list):
                    return items
    return None


def main():
    # Strategy: Confirm success if on confirmation page AND, when order data exists, it shows exactly one air fryer (id 2 or 3) with quantity 1.
    # If order details are absent, being on the confirmation page counts as success per training signals.
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    pathname = get_pathname(data)
    on_confirmation = (pathname == '/confirmation')

    items = get_order_items(data)

    allowed_air_fryers = {'2', '3'}

    if items is not None and isinstance(items, list) and len(items) > 0:
        # Validate exact single item order of one air fryer
        valid = False
        if on_confirmation and len(items) == 1:
            item = items[0]
            item_id = str(item.get('id')) if 'id' in item else None
            qty_raw = item.get('quantity')
            try:
                qty = int(qty_raw) if qty_raw is not None else None
            except Exception:
                qty = None
            if item_id in allowed_air_fryers and qty == 1:
                valid = True
        print('SUCCESS' if valid else 'FAILURE')
        return

    # Fallback when no order items available: rely on confirmation page
    print('SUCCESS' if on_confirmation else 'FAILURE')

if __name__ == '__main__':
    main()
