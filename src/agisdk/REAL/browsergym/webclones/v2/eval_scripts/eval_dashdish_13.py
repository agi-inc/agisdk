import json, sys

# Strategy:
# - Load final_state_diff.json and locate the cart from initialfinaldiff.added/updated.
# - Confirm: (1) at least one chicken burger/sandwich item, (2) at least one fries item,
#   (3) shipping option is Delivery, and (4) tip equals $2 (with robust type handling).
# - Print SUCCESS only if all conditions are met; otherwise print FAILURE.

def to_float(val):
    try:
        if isinstance(val, bool):
            return None
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            # remove any currency symbols or spaces
            s = val.strip().replace('$', '')
            return float(s)
    except Exception:
        return None
    return None


def find_cart(data):
    diff = data.get('initialfinaldiff', {})
    # Prefer 'added', then 'updated'
    for section in ['added', 'updated']:
        sec = diff.get(section, {})
        if isinstance(sec, dict) and 'cart' in sec and isinstance(sec.get('cart'), dict):
            cart = sec.get('cart')
            # Prefer cart that actually has cartItems or checkoutDetails
            if isinstance(cart.get('cartItems', None), list) or isinstance(cart.get('checkoutDetails', None), dict):
                return cart
    # Fallback: return any cart we find
    for section in ['added', 'updated']:
        sec = diff.get(section, {})
        if isinstance(sec, dict) and 'cart' in sec and isinstance(sec.get('cart'), dict):
            return sec.get('cart')
    return None


def is_chicken_burger(name: str) -> bool:
    if not isinstance(name, str):
        return False
    n = name.lower()
    if 'chicken' in n or 'mcchicken' in n:
        # Look for burger/sandwich/stack synonyms
        if any(k in n for k in ['burger', 'sandwich', 'mcchicken']):
            return True
    return False


def is_fries(name: str) -> bool:
    if not isinstance(name, str):
        return False
    n = name.lower()
    return 'fries' in n


def main():
    if len(sys.argv) < 2:
        print('FAILURE')
        return
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    cart = find_cart(data)
    if not isinstance(cart, dict):
        print('FAILURE')
        return

    items = cart.get('cartItems', [])
    if not isinstance(items, list) or len(items) == 0:
        print('FAILURE')
        return

    has_chicken_burger = False
    has_fries = False

    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get('name', '')
        if is_chicken_burger(name):
            has_chicken_burger = True
        if is_fries(name):
            has_fries = True

    # Shipping option must be Delivery
    checkout = cart.get('checkoutDetails', {}) if isinstance(cart.get('checkoutDetails'), dict) else {}
    shipping = checkout.get('shipping', {}) if isinstance(checkout.get('shipping'), dict) else {}
    ship_opt = shipping.get('shippingOption', '')
    is_delivery = isinstance(ship_opt, str) and ship_opt.strip().lower() == 'delivery'

    # Tip must be $2
    charges = checkout.get('charges', {}) if isinstance(checkout.get('charges'), dict) else {}
    tip_val = to_float(charges.get('tip', None))
    has_two_dollar_tip = tip_val is not None and abs(tip_val - 2.0) < 0.01

    if has_chicken_burger and has_fries and is_delivery and has_two_dollar_tip:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
