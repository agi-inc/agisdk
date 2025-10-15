import json, sys

# Verification script for task: "Order me 2 types of chicken curry from an indian restaurant. Need express delivery."
# Strategy:
# - Load final_state_diff.json and extract cart items and checkout shipping details from initialfinaldiff.added/updated.
# - Identify chicken curry dishes: name must include 'chicken' and one of curry-related keywords (e.g., curry, masala, korma, butter, etc.).
# - Ensure at least two DISTINCT qualifying dish names (normalized) and restaurant appears Indian (restaurantName contains 'indian', 'cuisine', or 'curry').
# - Confirm shippingOption is Delivery and deliveryOption is Express. Print SUCCESS only if all conditions hold, else FAILURE.

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_nested(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
        if cur is None:
            return None
    return cur


def extract_cart_items(data):
    items = []
    initial = data.get('initialfinaldiff', {})
    for section in ['added', 'updated']:
        cart = get_nested(initial, section, 'cart') or {}
        cis = cart.get('cartItems')
        if isinstance(cis, list):
            items.extend([x for x in cis if isinstance(x, dict)])
    return items


def extract_shipping(data):
    initial = data.get('initialfinaldiff', {})
    for section in ['added', 'updated']:
        shipping = get_nested(initial, section, 'cart', 'checkoutDetails', 'shipping')
        if isinstance(shipping, dict):
            return shipping
    return {}


def normalize_name(name):
    # Keep only lowercase letters and spaces; collapse multiple spaces.
    name = (name or '').lower()
    cleaned_chars = []
    prev_space = False
    for ch in name:
        if 'a' <= ch <= 'z':
            cleaned_chars.append(ch)
            prev_space = False
        elif ch.isspace():
            if not prev_space:
                cleaned_chars.append(' ')
                prev_space = True
        # ignore other characters
    cleaned = ''.join(cleaned_chars).strip()
    # remove common size qualifiers words if present
    for token in ['small', 'medium', 'large', 'half', 'full']:
        cleaned = cleaned.replace(' ' + token + ' ', ' ')
        if cleaned.endswith(' ' + token):
            cleaned = cleaned[:-(len(token)+1)]
        if cleaned.startswith(token + ' '):
            cleaned = cleaned[(len(token)+1):]
    cleaned = ' '.join([w for w in cleaned.split() if w])
    return cleaned


def is_indian_restaurant(name):
    if not name:
        return False
    n = name.lower()
    tokens = ['indian', 'cuisine', 'curry', 'indina']  # include common variants
    return any(t in n for t in tokens)


def is_chicken_curry_dish(name):
    if not name:
        return False
    n = name.lower()
    if 'chicken' not in n:
        return False
    # Require curry-like keywords to avoid non-curry items like tandoori or biryani
    curry_keywords = [
        'curry', 'masala', 'korma', 'butter', 'makhani', 'vindaloo', 'saag',
        'karahi', 'chettinad', 'jalfrezi', 'madras', 'do pyaza', 'dopiyaza', 'rogan josh',
        'rezala', 'handi', 'kolhapuri'
    ]
    if not any(kw in n for kw in curry_keywords):
        return False
    # Explicitly exclude common non-curry styles
    exclude_keywords = ['tandoori', 'biryani', 'wrap', 'roll', 'sandwich', 'burger', 'wing', 'kebab', 'kabob', 'kabab', 'grill']
    if any(ek in n for ek in exclude_keywords):
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print('FAILURE')
        return
    path = sys.argv[1]
    try:
        data = load_json(path)
    except Exception:
        print('FAILURE')
        return

    items = extract_cart_items(data)
    shipping = extract_shipping(data)

    # Validate shipping: Delivery + Express
    delivery_mode = (shipping.get('shippingOption') or '').strip().lower()
    delivery_option = (shipping.get('deliveryOption') or '').strip().lower()
    has_express = (delivery_mode == 'delivery' and delivery_option == 'express')

    # Collect qualifying chicken curry dishes from an Indian restaurant
    qualifying = []
    for it in items:
        name = it.get('name', '')
        rest = it.get('restaurantName', '')
        if is_chicken_curry_dish(name) and is_indian_restaurant(rest):
            qualifying.append(normalize_name(name))

    unique_types = set(qualifying)

    if has_express and len(unique_types) >= 2:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
