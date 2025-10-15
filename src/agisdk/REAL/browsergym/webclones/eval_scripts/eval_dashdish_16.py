import json, sys

def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def to_float(x):
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip().replace(',', '')
        # Remove any currency symbols
        s = s.replace('$', '')
        return float(s)
    except Exception:
        return None


def is_chicken_sandwich_item(item):
    name = (item.get('name') or '').strip().lower()
    desc = (item.get('description') or '').strip().lower()
    restaurant = (item.get('restaurantName') or '').strip().lower()

    if not name and not desc:
        return False

    # Exclusions for non-sandwich formats
    negatives = ['wing', 'wings', 'nugget', 'tender', 'tenders', 'salad', 'wrap', 'bowl']
    if any(neg in name for neg in negatives):
        return False

    # Identify sandwich-like items
    sandwich_markers = ['sandwich', 'sub', 'sando', "po' boy", 'po-boy', 'burger']
    is_sandwich_like = any(m in name for m in sandwich_markers)

    # Identify chicken-ness
    chicken_markers = ['chicken']
    is_chicken = any(m in name for m in chicken_markers) or any(m in desc for m in chicken_markers) or ('chicken' in restaurant and is_sandwich_like)

    # Common chicken sandwich variants without explicit 'chicken' in name
    # e.g., Chicken Parm(igiana) Sub often appears as 'Parmigiana Sub' with chicken context
    parm_like = ('parm' in name or 'parmigiana' in name) and is_sandwich_like

    # Known Ike's chicken classic that may omit 'chicken' in name in this dataset
    known_chicken_names = ['menage a trois']
    known_match = any(k in name for k in known_chicken_names)

    return is_sandwich_like and ( is_chicken or parm_like or known_match )


def extract_contexts(data):
    contexts = []
    root = data.get('initialfinaldiff', {})

    for section in ['added', 'updated']:
        part = root.get(section, {})
        cart = part.get('cart')
        if not isinstance(cart, dict):
            continue
        # Direct cart context
        cart_items = cart.get('cartItems')
        if isinstance(cart_items, list):
            total_amount = to_float(safe_get(cart, ['checkoutDetails', 'charges', 'totalAmount']))
            contexts.append({'source': 'cart', 'items': cart_items, 'total': total_amount})
        # Placed orders contexts
        food_orders = cart.get('foodOrders')
        if isinstance(food_orders, dict):
            for _, order in food_orders.items():
                if not isinstance(order, dict):
                    continue
                order_items = order.get('cartItems')
                order_total = to_float(safe_get(order, ['checkoutDetails', 'charges', 'totalAmount']))
                if isinstance(order_items, list):
                    contexts.append({'source': 'foodOrders', 'items': order_items, 'total': order_total})
    return contexts


def verify(data):
    contexts = extract_contexts(data)

    # We need any context that contains a chicken sandwich item and has total under $25
    for ctx in contexts:
        items = ctx.get('items') or []
        total = ctx.get('total')
        has_target = any(is_chicken_sandwich_item(it) for it in items)
        if has_target and (total is not None) and (total < 25.0):
            return True
    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    result = verify(data)
    print('SUCCESS' if result else 'FAILURE')

if __name__ == '__main__':
    main()
