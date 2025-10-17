import json, sys

# Strategy in code:
# 1) Load final_state_diff.json and find cart + charges.
# 2) Success requires: at least one cart item that clearly indicates Asian cuisine (via keywords in
#    restaurantName, item name, or description) AND total amount > 0 and < 45.
#    Otherwise, print FAILURE.


def safe_get(dic, keys, default=None):
    cur = dic
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def to_float(val, default=0.0):
    try:
        if val is None:
            return default
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip().replace('$', '')
        return float(s)
    except Exception:
        return default


ASIAN_KEYWORDS = [
    # Broad cuisine/region terms
    'thai', 'japanese', 'korean', 'chinese', 'vietnamese', 'taiwanese', 'mongolian', 'filipino',
    'indian', 'pakistani', 'nepalese', 'sri lankan', 'laotian', 'lao', 'cambodian', 'khmer',
    'malaysian', 'singaporean', 'indonesian',
    # Common dishes/terms
    'ramen', 'sushi', 'teriyaki', 'yakitori', 'udon', 'tempura', 'okonomiyaki', 'tonkatsu',
    'bibimbap', 'kimchi', 'kimbap', 'soondubu', 'jajangmyeon', 'tteokbokki', 'kbbq',
    'szechuan', 'sichuan', 'cantonese', 'dim sum', 'dumpling', 'bao', 'xiao long bao',
    'pho', 'banh mi', 'bun bo', 'bun cha',
    'pad thai', 'pad see ew', 'tom yum', 'tom kha', 'larb', 'green curry', 'red curry', 'drunken noodles',
]

# Some explicit non-Asian markers (used only to avoid false positives if needed)
NON_ASIAN_HINTS = [
    'pizza', 'burger', 'fries', 'taco', 'burrito', 'quesadilla', 'pasta', 'sandwich', 'hot dog', 'nacho'
]


def text_has_any(text, keywords):
    if not text:
        return False
    t = str(text).lower()
    return any(kw in t for kw in keywords)


def item_is_asian(item):
    fields = [
        item.get('restaurantName', ''),
        item.get('name', ''),
        item.get('description', ''),
    ]
    # If any field includes an explicit non-Asian hint and none include Asian keywords, treat as non-Asian
    has_asian = any(text_has_any(f, ASIAN_KEYWORDS) for f in fields)
    if has_asian:
        return True
    # If clearly non-Asian terms present without Asian terms, mark as non-Asian
    has_non_asian = any(text_has_any(f, NON_ASIAN_HINTS) for f in fields)
    if has_non_asian and not has_asian:
        return False
    # Default to False unless Asian indicators found
    return False


def compute_total(cart):
    charges = safe_get(cart, ['checkoutDetails', 'charges'], {}) or {}
    total = to_float(charges.get('totalAmount'), 0.0)
    if total > 0:
        return total
    # Fallback: sum of item final prices if charges missing/zero
    items = cart.get('cartItems', []) or []
    s = 0.0
    for it in items:
        # Prefer finalPrice, else basePrice
        fp = it.get('finalPrice')
        if fp is None:
            fp = it.get('basePrice')
        s += to_float(fp, 0.0)
    return s


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    cart = safe_get(data, ['initialfinaldiff', 'added', 'cart'], {}) or {}
    items = cart.get('cartItems', []) or []
    if not items:
        print("FAILURE")
        return

    # Check for at least one Asian item
    asian_present = any(item_is_asian(it) for it in items)

    # Compute total and verify under budget
    total = compute_total(cart)
    under_budget = (total > 0) and (total < 45.0)

    if asian_present and under_budget:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == '__main__':
    main()
