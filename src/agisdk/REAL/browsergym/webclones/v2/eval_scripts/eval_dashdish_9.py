import json, sys

# Strategy:
# - Load final_state_diff.json and extract cart from initialfinaldiff.added/updated.
# - Success if: (a) cart has >=1 item, (b) every item's restaurantName == 'Taco Boys' (case-insensitive),
#   and (c) checkoutDetails.charges.totalAmount >= 20. If totalAmount missing, fallback to sum of item finalPrice.

def safe_get(d, *keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur


def to_float(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x.strip().replace('$',''))
        except:
            return None
    return None


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    initdiff = data.get('initialfinaldiff', {})

    cart = None
    for section in ('added', 'updated'):
        sec = initdiff.get(section, {})
        if isinstance(sec, dict) and 'cart' in sec and isinstance(sec['cart'], dict):
            cart = sec['cart']
            break

    if not isinstance(cart, dict):
        print("FAILURE")
        return

    cart_items = cart.get('cartItems')
    if not isinstance(cart_items, list) or len(cart_items) == 0:
        print("FAILURE")
        return

    # Verify all items are from Taco Boys
    all_taco_boys = True
    for item in cart_items:
        if not isinstance(item, dict):
            all_taco_boys = False
            break
        rname = item.get('restaurantName')
        if not isinstance(rname, str) or rname.strip().lower() != 'taco boys':
            all_taco_boys = False
            break
    if not all_taco_boys:
        print("FAILURE")
        return

    # Check total amount at checkout
    total_amount = safe_get(cart, 'checkoutDetails', 'charges', 'totalAmount')
    total_val = to_float(total_amount)

    if total_val is None:
        # Fallback: sum finalPrice of items
        subtotal = 0.0
        any_price = False
        for it in cart_items:
            fp = to_float(it.get('finalPrice'))
            if fp is not None:
                subtotal += fp
                any_price = True
        total_val = subtotal if any_price else None

    if total_val is None or total_val < 20.0:
        print("FAILURE")
        return

    print("SUCCESS")

if __name__ == '__main__':
    main()
