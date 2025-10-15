import json, sys

def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur

# Strategy:
# - Gather all items from cart.cartItems and any foodOrders.*.cartItems found in the diff JSON.
# - Detect noodle and soup dishes via robust keyword sets; infer Asian context via restaurant or dish keywords.
# - Success if there's at least one Asian-context noodle item and one Asian-context soup item (same item can satisfy both).

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    items = []
    # Collect cart items from added diff
    cart_items = safe_get(data, ["initialfinaldiff", "added", "cart", "cartItems"], [])
    if isinstance(cart_items, list):
        items.extend(cart_items)

    # Collect items from foodOrders inside cart in added diff
    food_orders = safe_get(data, ["initialfinaldiff", "added", "cart", "foodOrders"], {})
    if isinstance(food_orders, dict):
        for order in food_orders.values():
            ci = order.get("cartItems", [])
            if isinstance(ci, list):
                items.extend(ci)

    # Also check differences.foodOrders.added as fallback
    diff_food_orders_added = safe_get(data, ["differences", "foodOrders", "added"], {})
    if isinstance(diff_food_orders_added, dict):
        for order in diff_food_orders_added.values():
            ci = order.get("cartItems", [])
            if isinstance(ci, list):
                items.extend(ci)

    # Define keyword sets
    noodle_kw = [
        "noodle", "noodles", "chow mein", "lo mein", "pad thai", "udon", "ramen",
        "yakisoba", "chow fun", "ho fun", "mien", "mee goreng", "mi quang",
        "laksa", "bihun", "vermicelli", "dan dan"
    ]
    soup_kw = [
        "soup", "tom yum", "hot & sour", "hot and sour", "wonton", "miso", "egg drop",
        "tom kha", "laksa", "pho", "ramen"
    ]
    # Asian context keywords (in restaurant or dish/description)
    asian_kw = [
        # Cuisines / regions / terms
        "thai", "china", "chinese", "asian", "sushi", "ramen", "pho", "vietnam",
        "vietnamese", "korean", "japanese", "teriyaki", "wok", "dim sum",
        "kung", "bao", "udon", "soba", "yakisoba", "bento", "kimchi", "bibimbap",
        "saigon", "tokyo", "kyoto", "bangkok", "singapore", "malay", "malaysian", "indonesian",
        "tandoori", "indian", "szechuan", "sichuan", "mandarin", "cantonese", "hong kong",
        # Dish-specific Asian markers
        "pad thai", "chow mein", "lo mein", "chow fun", "ho fun", "tom yum", "tom kha",
        "hot & sour", "hot and sour", "wonton", "dan dan", "laksa"
    ]

    def text_fields(item):
        name = str(item.get("name", ""))
        desc = str(item.get("description", ""))
        rest = str(item.get("restaurantName", ""))
        return name.lower(), desc.lower(), rest.lower()

    def contains_any(s, kws):
        return any(k in s for k in kws)

    has_noodle = False
    has_soup = False

    noodle_asian = False
    soup_asian = False

    for it in items:
        name, desc, rest = text_fields(it)
        combined = f"{name} {desc}".lower()

        is_noodle = contains_any(name, noodle_kw) or contains_any(desc, noodle_kw)
        is_soup = contains_any(name, soup_kw) or contains_any(desc, soup_kw)

        # Asian inference from restaurant or dish context
        asian_context = contains_any(rest, asian_kw) or contains_any(combined, asian_kw)

        if is_noodle:
            has_noodle = True
            if asian_context:
                noodle_asian = True
        if is_soup:
            has_soup = True
            if asian_context:
                soup_asian = True
        # Noodle-soup combos: pho/ramen/laksa/udon/soba imply both
        if not is_noodle and not is_soup:
            if any(k in combined for k in ["pho", "ramen", "laksa", "udon", "soba"]):
                has_noodle = True
                has_soup = True
                if asian_context:
                    noodle_asian = True
                    soup_asian = True

    success_basic = has_noodle and has_soup
    success_asian = (noodle_asian and soup_asian) if success_basic else False

    print("SUCCESS" if success_asian else "FAILURE")
except Exception:
    print("FAILURE")