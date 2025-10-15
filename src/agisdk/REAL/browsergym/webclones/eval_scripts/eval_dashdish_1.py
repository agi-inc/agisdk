import json, sys

def to_float(val):
    if val is None:
        return None
    try:
        s = str(val).strip()
        # Remove currency symbols and commas if any
        for ch in ['$', ',', '€', '£']:
            s = s.replace(ch, '')
        return float(s)
    except Exception:
        return None


def get_cart_items(data):
    items = []
    initialfinaldiff = data.get('initialfinaldiff', {})
    for section in ['added', 'updated']:
        sec = initialfinaldiff.get(section, {})
        cart = sec.get('cart')
        if isinstance(cart, dict):
            ci = cart.get('cartItems')
            if isinstance(ci, list):
                items.extend([x for x in ci if isinstance(x, dict)])
    return items


def get_item_price(item):
    # Prefer finalPrice, else try basePrice+extraCost, else price
    final_price = item.get('finalPrice')
    fp = to_float(final_price)
    if fp is not None:
        return fp
    bp = to_float(item.get('basePrice'))
    ec = to_float(item.get('extraCost'))
    if bp is not None:
        if ec is None:
            ec = 0.0
        return bp + ec
    p = to_float(item.get('price'))
    return p


def is_pizza(item):
    name = item.get('name')
    if not isinstance(name, str):
        return False
    return 'pizza' in name.lower()


def verify(data):
    items = get_cart_items(data)
    if not items:
        return False
    pizza_items = [it for it in items if is_pizza(it) and (to_float(it.get('quantity')) is None or to_float(it.get('quantity')) >= 1)]
    if not pizza_items:
        return False
    # All pizza items present should be strictly under $30
    for it in pizza_items:
        price = get_item_price(it)
        if price is None:
            return False
        if price >= 30.0:
            return False
    return True


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
        result = verify(data)
        print('SUCCESS' if result else 'FAILURE')
    except Exception:
        # On any unexpected error, mark as failure
        print('FAILURE')

if __name__ == '__main__':
    main()