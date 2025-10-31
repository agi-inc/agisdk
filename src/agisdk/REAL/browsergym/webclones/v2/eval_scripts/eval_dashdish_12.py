import json, sys

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

# Determine if a text suggests a rice-containing dish
def item_contains_rice(item):
    name = (item.get('name') or '')
    desc = (item.get('description') or '')
    rest = (item.get('restaurantName') or '')
    text = f"{name} {desc} {rest}".lower()

    strong_keywords = [
        'rice', 'fried rice', 'biryani', 'risotto', 'donburi', 'bibimbap',
        'poke bowl', 'sushi bowl', 'chirashi', 'onigiri', 'nasi', 'pilaf', 'pilau',
        'paella', 'jambalaya', 'katsudon', 'gyudon', 'bento', 'rice bowl', 'ricebowl',
        'teriyaki bowl', 'curry bowl'
    ]
    # Negative indicators for generic 'bowl'
    negative_for_bowl = ['soup', 'salad', 'fries', 'wing', 'wings', 'chips']

    if any(kw in text for kw in strong_keywords):
        return True
    # Heuristic: many menu items called 'bowl' are rice bowls in this domain
    if 'bowl' in text and not any(neg in text for neg in negative_for_bowl):
        return True
    return False

# Extract numeric total amount robustly
def get_total_amount(order):
    charges = ((order or {}).get('checkoutDetails') or {}).get('charges') or {}
    amt = charges.get('totalAmount')
    try:
        return float(amt)
    except (TypeError, ValueError):
        return None

# Collect orders from multiple plausible paths in the diff
def collect_orders(data):
    orders = []
    seen_ids = set()

    # Path 1: initialfinaldiff.added.cart.foodOrders
    path1 = (((data.get('initialfinaldiff') or {}).get('added') or {}).get('cart') or {}).get('foodOrders')
    if isinstance(path1, dict):
        for k, v in path1.items():
            if isinstance(v, dict):
                oid = v.get('orderId') or f"path1-{k}"
                if oid not in seen_ids:
                    orders.append(v)
                    seen_ids.add(oid)

    # Path 2: differences.foodOrders.added
    path2 = (((data.get('differences') or {}).get('foodOrders') or {}).get('added'))
    if isinstance(path2, dict):
        for k, v in path2.items():
            if isinstance(v, dict):
                oid = v.get('orderId') or f"path2-{k}"
                if oid not in seen_ids:
                    orders.append(v)
                    seen_ids.add(oid)

    return orders


def verify(path):
    data = load_json(path)
    orders = collect_orders(data)

    if not orders:
        return False

    # Success if there exists at least one order where:
    # - totalAmount < 30
    # - there is at least one cart item
    # - every cart item appears to be a rice-containing dish
    for order in orders:
        total = get_total_amount(order)
        items = order.get('cartItems') or []
        if total is None or total >= 30:
            continue
        if not items:
            continue
        if all(item_contains_rice(it) for it in items):
            return True

    return False

if __name__ == '__main__':
    try:
        file_path = sys.argv[1]
    except IndexError:
        print('FAILURE')
        sys.exit(0)

    result = verify(file_path)
    print('SUCCESS' if result else 'FAILURE')
