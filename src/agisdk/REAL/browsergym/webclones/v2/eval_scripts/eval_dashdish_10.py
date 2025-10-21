import sys, json

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Recursively collect all lists under any 'cartItems' key in the JSON
# This avoids overfitting to a specific nesting (added/updated/etc.)
def find_cart_items(node):
    items = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'cartItems' and isinstance(v, list):
                # ensure only dict items are considered as cart entries
                items.extend([x for x in v if isinstance(x, dict)])
            else:
                items.extend(find_cart_items(v))
    elif isinstance(node, list):
        for el in node:
            items.extend(find_cart_items(el))
    return items

# Normalize text for robust matching
def norm_text(s):
    try:
        return ' '.join(str(s).lower().split())
    except Exception:
        return ''

# Determine if an item satisfies the goal: lemon pepper wings from Wingstop
# Strategy: require restaurant contains "wingstop" and item text contains
# both "lemon" and "pepper" and also contains "wing" (to avoid matching fries, etc.)

def item_matches(item):
    restaurant = norm_text(item.get('restaurantName', ''))
    if 'wingstop' not in restaurant:
        return False

    # Combine relevant textual fields to capture naming variations
    name = norm_text(item.get('name', ''))
    desc = norm_text(item.get('description', ''))
    prefs = norm_text(item.get('preferences', ''))
    size = norm_text(item.get('size', ''))
    combined = ' '.join([name, desc, prefs, size])

    has_lemon = 'lemon' in combined
    has_pepper = 'pepper' in combined
    has_wing = 'wing' in combined  # matches wing/wings

    if has_lemon and has_pepper and has_wing:
        # Optionally ensure quantity positive if present
        qty = item.get('quantity')
        if qty is None:
            return True
        try:
            return float(qty) > 0
        except Exception:
            return True
    return False


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

    items = find_cart_items(data)
    success = False
    for it in items:
        if item_matches(it):
            success = True
            break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
