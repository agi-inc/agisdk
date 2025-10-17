import sys, json

def to_float(x):
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def contains_noodle(text: str) -> bool:
    if not isinstance(text, str):
        return False
    t = text.lower()
    # Core keyword plus a few common variants to generalize modestly
    keywords = [
        'noodle',      # matches noodle/noodles
        'ramen',
        'udon',
        'soba',
        'pho',
        'lo mein',
        'chow mein',
        'pad thai',
        'vermicelli',
    ]
    return any(k in t for k in keywords)


def is_noodle_item(item: dict) -> bool:
    name = item.get('name', '')
    desc = item.get('description', '')
    return contains_noodle(name) or contains_noodle(desc)


def any_noodle(items):
    if not isinstance(items, list):
        return False
    for it in items:
        if isinstance(it, dict) and is_noodle_item(it) and to_float(it.get('quantity', 1)) != 0:
            return True
    return False


def get_total_amount(charges_container: dict):
    if not isinstance(charges_container, dict):
        return None
    return to_float(charges_container.get('totalAmount'))


def evaluate_order_obj(order_obj: dict):
    # Expect structure similar to order with cartItems and checkoutDetails.charges
    items = order_obj.get('cartItems', []) if isinstance(order_obj, dict) else []
    has_noodle = any_noodle(items)
    charges = None
    if isinstance(order_obj, dict):
        charges = order_obj.get('checkoutDetails', {}).get('charges', {})
    total = get_total_amount(charges)
    return has_noodle, total


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    added = (data.get('initialfinaldiff') or {}).get('added') or {}
    cart = added.get('cart') or {}

    # 1) Prefer completed orders if present
    orders = cart.get('foodOrders')
    order_candidates = []
    if isinstance(orders, dict) and orders:
        order_candidates.extend(list(orders.values()))
    elif isinstance(orders, list) and orders:
        order_candidates.extend(orders)

    # Fallback: differences.foodOrders.added
    if not order_candidates:
        diffs_orders = ((data.get('differences') or {}).get('foodOrders') or {}).get('added')
        if isinstance(diffs_orders, dict) and diffs_orders:
            order_candidates.extend(list(diffs_orders.values()))
        elif isinstance(diffs_orders, list) and diffs_orders:
            order_candidates.extend(diffs_orders)

    # Evaluate any order that meets both conditions: noodles present and total < 26
    for ord_obj in order_candidates:
        has_noodle, total = evaluate_order_obj(ord_obj)
        if has_noodle and (total is not None) and (total < 26):
            print('SUCCESS')
            return

    # 2) Evaluate current cart if no qualifying order found
    cart_items = cart.get('cartItems', [])
    has_noodle_in_cart = any_noodle(cart_items)
    charges = (cart.get('checkoutDetails') or {}).get('charges') or {}
    total = get_total_amount(charges)

    if has_noodle_in_cart and (total is not None) and (total < 26):
        print('SUCCESS')
        return

    print('FAILURE')

if __name__ == '__main__':
    main()
