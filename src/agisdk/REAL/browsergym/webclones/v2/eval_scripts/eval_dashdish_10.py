import json, sys

# Strategy:
# - Recursively search the JSON for any order objects containing cartItems and checkoutDetails.charges.totalAmount
# - A state is SUCCESS if any order includes at least one item with 'fries' in its name/description (case-insensitive)
#   AND the totalAmount is <= 20. Otherwise, it's FAILURE.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def to_float(val):
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            s = val.strip().replace('$', '').replace(',', '')
            return float(s)
    except Exception:
        return None
    return None


def find_orders(obj):
    orders = []

    def recurse(o):
        if isinstance(o, dict):
            # Identify an order-like object
            if 'cartItems' in o and isinstance(o.get('cartItems'), list) and 'checkoutDetails' in o:
                cd = o.get('checkoutDetails')
                if isinstance(cd, dict):
                    charges = cd.get('charges', {})
                    if isinstance(charges, dict) and 'totalAmount' in charges:
                        orders.append(o)
            for v in o.values():
                recurse(v)
        elif isinstance(o, list):
            for it in o:
                recurse(it)
    recurse(obj)
    return orders


def contains_fries(text):
    if not text:
        return False
    t = text.lower()
    return 'fries' in t


def order_has_fries(order):
    items = order.get('cartItems', [])
    for it in items:
        name = it.get('name', '')
        desc = it.get('description', '')
        if contains_fries(name) or contains_fries(desc):
            return True
    return False


def order_total(order):
    charges = order.get('checkoutDetails', {}).get('charges', {})
    return to_float(charges.get('totalAmount'))


def main():
    path = sys.argv[1]
    data = load_json(path)

    orders = find_orders(data)

    success = False
    for o in orders:
        total = order_total(o)
        has_fries = order_has_fries(o)
        if total is None:
            continue
        if has_fries and total <= 20.0:
            success = True
            break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()