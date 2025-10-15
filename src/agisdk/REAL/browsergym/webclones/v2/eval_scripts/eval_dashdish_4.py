import json
import sys

# Strategy:
# - Load final_state_diff.json and extract cart/cartItems robustly from various possible locations.
# - Determine if at least one item was ordered, all items are rice-based (heuristic keywords),
#   and the total amount (charges.totalAmount if present, else sum of item finalPrice/price) is < 30.
# - Print SUCCESS if all conditions met; otherwise print FAILURE.


def deep_find_cart(d):
    """Attempt to find a cart dict that contains cartItems anywhere in the structure."""
    if isinstance(d, dict):
        if 'cartItems' in d:
            return d
        for v in d.values():
            res = deep_find_cart(v)
            if res is not None:
                return res
    elif isinstance(d, list):
        for v in d:
            res = deep_find_cart(v)
            if res is not None:
                return res
    return None


def get_cart(data):
    # Try common locations first
    paths = [
        ('initialfinaldiff', 'added', 'cart'),
        ('initialfinaldiff', 'updated', 'cart'),
        ('initialfinaldiff', 'cart'),
    ]
    for p in paths:
        cur = data
        ok = True
        for k in p:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and isinstance(cur, dict) and 'cartItems' in cur:
            return cur
    # Fallback: deep search
    return deep_find_cart(data)


def to_float(x):
    try:
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            s = x.strip().replace('$', '')
            return float(s)
    except Exception:
        return None
    return None


POSITIVE_KEYWORDS = [
    'rice', 'biryani', 'bowl', 'sushi', 'donburi', 'bibimbap', 'risotto', 'poke bowl', 'poke', 'on rice', 'over rice'
]

# Some words strongly indicate non-rice meals; used as a weak guard when ambiguous
NEGATIVE_KEYWORDS = [
    'wings', 'fries', 'pizza', 'burger', 'sandwich', 'wrap', 'taco', 'tacos', 'noodle', 'noodles'
]


def is_rice_meal(item):
    name = (item.get('name') or '')
    desc = (item.get('description') or '')
    rest = (item.get('restaurantName') or '')
    text = f"{name} {desc} {rest}".lower()
    # If any explicit positive keyword present, accept
    if any(kw in text for kw in POSITIVE_KEYWORDS):
        return True
    # If contains strong negatives, reject
    if any(kw in text for kw in NEGATIVE_KEYWORDS):
        return False
    # Heuristic: many Asian-style "bowl" dishes contain rice, handled above.
    # If it's an Asian cuisine term without explicit negatives, we can consider some patterns
    asian_cues = ['bento', 'teriyaki', 'katsu', 'gyudon', 'don', 'korean', 'japanese']
    if any(kw in text for kw in asian_cues):
        # Likely served with rice; accept cautiously
        return True
    return False


def compute_total(cart, items):
    # Prefer checkoutDetails.charges.totalAmount if valid and > 0
    charges = {}
    try:
        charges = (cart.get('checkoutDetails') or {}).get('charges') or {}
    except Exception:
        charges = {}
    total = to_float(charges.get('totalAmount'))
    if total is not None and total > 0:
        return total
    # Fallback: sum item finalPrice or price
    s = 0.0
    any_price = False
    for it in items:
        val = it.get('finalPrice')
        if val is None:
            val = it.get('price')
        f = to_float(val)
        if f is not None:
            s += f
            any_price = True
    return s if any_price else None


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r') as f:
            data = json.load(f)
        cart = get_cart(data)
        if not cart:
            print('FAILURE')
            return
        items = cart.get('cartItems') or []
        if not isinstance(items, list) or len(items) == 0:
            print('FAILURE')
            return
        # All items must be rice meals
        if not all(is_rice_meal(it) for it in items):
            print('FAILURE')
            return
        total = compute_total(cart, items)
        # If total is missing or not a number, fail to be safe
        if total is None:
            print('FAILURE')
            return
        # Must be strictly less than $30
        if total < 30:
            print('SUCCESS')
        else:
            print('FAILURE')
    except Exception:
        print('FAILURE')


if __name__ == '__main__':
    main()
