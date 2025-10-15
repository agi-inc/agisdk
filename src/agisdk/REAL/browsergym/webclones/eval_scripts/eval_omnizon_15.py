import json
import sys

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_section(initialfinaldiff, section_name):
    if not isinstance(initialfinaldiff, dict):
        return {}
    sec = initialfinaldiff.get(section_name, {})
    return sec if isinstance(sec, dict) else {}


def extract_orders_from_section(section):
    # Expected path: section -> 'order' -> 'orders' -> dict of index->order
    orders = []
    order_container = section.get('order', {}) if isinstance(section, dict) else {}
    if isinstance(order_container, dict):
        orders_dict = order_container.get('orders', {})
        if isinstance(orders_dict, dict):
            for v in orders_dict.values():
                if isinstance(v, dict):
                    orders.append(v)
        elif isinstance(orders_dict, list):
            for v in orders_dict:
                if isinstance(v, dict):
                    orders.append(v)
    return orders


def has_jacket_in_orders(orders):
    # Based on training data, jacket item ids are '65' and '66'
    jacket_ids = {"65", "66"}
    for order in orders:
        items = order.get('items', [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get('id')
            if item_id is None:
                continue
            if str(item_id) in jacket_ids:
                return True
    return False


def get_pathnames(initialfinaldiff):
    pathnames = set()
    for sec_name in ['updated', 'added']:
        sec = get_section(initialfinaldiff, sec_name)
        router = sec.get('router', {}) if isinstance(sec, dict) else {}
        if isinstance(router, dict):
            loc = router.get('location', {})
            if isinstance(loc, dict):
                pn = loc.get('pathname')
                if isinstance(pn, str):
                    pathnames.add(pn)
    return pathnames


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return

    try:
        data = load_json(path)
    except Exception:
        print('FAILURE')
        return

    initialfinaldiff = data.get('initialfinaldiff', {})
    if not isinstance(initialfinaldiff, dict):
        print('FAILURE')
        return

    # Collect orders from both added and updated sections to be robust
    all_orders = []
    for sec_name in ['added', 'updated']:
        sec = get_section(initialfinaldiff, sec_name)
        all_orders.extend(extract_orders_from_section(sec))

    has_jacket_order = has_jacket_in_orders(all_orders)

    # Confirm that the flow reached the confirmation page (indicates order placed)
    pathnames = get_pathnames(initialfinaldiff)
    on_confirmation = '/confirmation' in pathnames

    if has_jacket_order and on_confirmation:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()