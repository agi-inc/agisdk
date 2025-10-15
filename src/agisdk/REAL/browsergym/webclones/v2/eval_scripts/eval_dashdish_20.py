import sys, json

# Strategy inside code:
# - Load final_state_diff.json from sys.argv[1]
# - Extract the most relevant 'cart' object from initialfinaldiff (prefer the one with most items across 'added' and 'updated')
# - Confirm shipping option indicates Pickup
# - Confirm cart contains two specific sandwiches: Menage a Trois and Godfather, both from Ike's (restaurant name includes 'ike')
# - Be tolerant to name variations (case-insensitive, token presence) and allow extra items in cart


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def normalize(s):
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    # normalize some common punctuation variants
    s = s.replace("’", "'").replace("‘", "'").replace("`", "'")
    return s


def extract_best_cart(data):
    initial = data.get("initialfinaldiff", {})
    candidates = []
    for section in ("added", "updated"):
        sec = initial.get(section, {})
        cart = sec.get("cart")
        if isinstance(cart, dict):
            candidates.append(cart)
    # Fallback: sometimes cart may be directly under initialfinaldiff
    direct_cart = initial.get("cart")
    if isinstance(direct_cart, dict):
        candidates.append(direct_cart)
    if not candidates:
        return None

    def items_len(c):
        items = c.get("cartItems")
        return len(items) if isinstance(items, list) else 0

    # choose the cart with the most items as best representative of final state
    candidates.sort(key=items_len, reverse=True)
    return candidates[0]


def is_from_ikes(restaurant_name):
    r = normalize(restaurant_name)
    # Broad match to cover variants like "ike's", "ike’s love & sandwiches"
    return "ike" in r


def name_matches_menage(name):
    n = normalize(name)
    # Accept common variations: must include both menage (or ménage) and trois
    if ("menage" in n and "trois" in n):
        return True
    # Also handle accented variant if present in original string
    orig = name.lower() if isinstance(name, str) else ""
    if ("ménage" in orig and "trois" in n):
        return True
    return False


def name_matches_godfather(name):
    n = normalize(name)
    return "godfather" in n  # allow with/without leading 'the'


def is_pickup(shipping_obj):
    if not isinstance(shipping_obj, dict):
        return False
    opt = shipping_obj.get("shippingOption")
    if not isinstance(opt, str):
        return False
    return "pickup" in opt.strip().lower()


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return

    try:
        data = load_json(path)
    except Exception:
        print("FAILURE")
        return

    cart = extract_best_cart(data)
    if not isinstance(cart, dict):
        print("FAILURE")
        return

    # Verify pickup
    shipping = (
        cart.get("checkoutDetails", {}).get("shipping")
        if isinstance(cart.get("checkoutDetails"), dict)
        else None
    )
    if not is_pickup(shipping):
        print("FAILURE")
        return

    items = cart.get("cartItems")
    if not isinstance(items, list) or len(items) == 0:
        print("FAILURE")
        return

    found_menage = False
    found_godfather = False

    for it in items:
        if not isinstance(it, dict):
            continue
        name = it.get("name", "")
        restaurant = it.get("restaurantName", "")
        if not is_from_ikes(restaurant):
            continue
        if not found_menage and name_matches_menage(name):
            found_menage = True
        if not found_godfather and name_matches_godfather(name):
            found_godfather = True
        if found_menage and found_godfather:
            break

    if found_menage and found_godfather:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
