import json, sys

def find_cart(data):
    idiff = data.get('initialfinaldiff', {})
    # Prefer 'added', then 'updated'
    for section in ('added', 'updated'):
        sec = idiff.get(section, {})
        cart = sec.get('cart') if isinstance(sec, dict) else None
        if isinstance(cart, dict) and cart:
            return cart
    # Fallback: search recursively for a 'cart' dict
    def _search(obj):
        if isinstance(obj, dict):
            if 'cart' in obj and isinstance(obj['cart'], dict):
                return obj['cart']
            for v in obj.values():
                res = _search(v)
                if res is not None:
                    return res
        elif isinstance(obj, list):
            for v in obj:
                res = _search(v)
                if res is not None:
                    return res
        return None
    return _search(idiff)


def is_delivery_to_home(shipping):
    if not isinstance(shipping, dict):
        return False
    option = str(shipping.get('shippingOption', '')).strip().lower()
    if option != 'delivery':
        return False
    address = str(shipping.get('address', '')).strip().lower()
    # Consider it the user's house if it contains the distinctive home street name used in training data
    # Be lenient to formatting, just check for 'portofino' token (as in '710 Portofino Ln, Foster City, CA 94404, USA')
    if 'portofino' not in address:
        return False
    return True


def coffee_like_quantity(cart_items):
    # Accept common coffee beverages; include 'latte' to cover Matcha Latte success example
    coffee_keywords = [
        'coffee', 'espresso', 'cappuccino', 'latte', 'macchiato', 'americano', 'mocha',
        'cold brew', 'cortado', 'flat white', 'affogato', 'café', 'cafe', 'drip', 'breve',
        'frappuccino', 'matcha'
    ]
    total_qty = 0
    for item in cart_items or []:
        name = str(item.get('name', '')).lower()
        if any(k in name for k in coffee_keywords):
            try:
                qty = int(item.get('quantity', 0))
            except Exception:
                # Try to coerce numeric strings; otherwise treat as 0
                try:
                    qty = int(float(str(item.get('quantity'))))
                except Exception:
                    qty = 0
            total_qty += qty
    return total_qty


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

    cart = find_cart(data)
    if not isinstance(cart, dict):
        print('FAILURE')
        return

    shipping = (cart.get('checkoutDetails') or {}).get('shipping', {})
    if not is_delivery_to_home(shipping):
        print('FAILURE')
        return

    items = cart.get('cartItems', [])
    coffee_qty = coffee_like_quantity(items)

    # Task requires exactly ONE coffee ordered (not multiple) and delivered to house
    if coffee_qty == 1:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()