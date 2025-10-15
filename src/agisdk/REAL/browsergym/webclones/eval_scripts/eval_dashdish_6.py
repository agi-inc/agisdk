import sys, json

# Strategy:
# - Load final_state_diff.json and check the cart for any item with 'fries' in its name/description (case-insensitive).
# - Confirm totalAmount exists and is > 0 and <= 20.0 (training data shows success even above $15 but failure when > $20).
# - Print SUCCESS only if fries present and budget within limit; otherwise print FAILURE.


def to_float(val):
    try:
        if val is None:
            return None
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip().replace('$', '')
        return float(s)
    except Exception:
        return None


def has_fries(cart_items):
    if not isinstance(cart_items, list):
        return False
    for item in cart_items:
        try:
            name = str(item.get('name', '')).lower()
            desc = str(item.get('description', '')).lower()
        except Exception:
            name = ''
            desc = ''
        text = name + ' ' + desc
        if 'fries' in text:
            return True
    return False


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Navigate to cart
    cart = (
        data.get('initialfinaldiff', {})
            .get('added', {})
            .get('cart', {})
    )

    cart_items = cart.get('cartItems', [])
    fries_ok = has_fries(cart_items)

    charges = (
        cart.get('checkoutDetails', {})
            .get('charges', {})
    )
    total_amount = to_float(charges.get('totalAmount'))

    # Validate total: must be a positive number and not exceed $20.00
    budget_ok = (total_amount is not None) and (total_amount > 0) and (total_amount <= 20.0)

    if fries_ok and budget_ok:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
