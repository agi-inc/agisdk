import sys, json

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Recursively collect all cartItems lists outside any 'deleted' subtree
def collect_cart_items(obj, in_deleted=False):
    items = []
    if isinstance(obj, dict):
        # If we encounter a 'deleted' key, mark its subtree as deleted
        for k, v in obj.items():
            if k == 'deleted':
                # Traverse but mark as deleted (to ignore cartItems there)
                items.extend(collect_cart_items(v, in_deleted=True))
            else:
                # If this dict itself has a 'cartItems' key, capture if not in deleted
                if k == 'cartItems' and not in_deleted and isinstance(v, list):
                    items.extend(v)
                items.extend(collect_cart_items(v, in_deleted=in_deleted))
    elif isinstance(obj, list):
        for v in obj:
            items.extend(collect_cart_items(v, in_deleted=in_deleted))
    return items

# Determine if an item string indicates chicken meat
def is_chicken(text):
    t = text.lower()
    if 'chicken' not in t:
        return False
    negative = ['broth', 'stock', 'seasoning', 'flavor', 'bouillon', 'soup', 'noodle', 'noodles', 'ramen']
    positives = ['ground', 'breast', 'thigh', 'wing', 'drum', 'drumstick', 'rotisserie', 'whole', 'tender', 'steak', 'roast', 'patty', 'ribs', 'sirloin', 'boneless', 'bone-in', 'mince', 'minced', 'filet', 'fillet', 'organic', 'fresh']
    if any(n in t for n in negative) and not any(p in t for p in positives):
        return False
    return True

# Determine if an item string indicates beef meat
def is_beef(text):
    t = text.lower()
    if 'beefsteak tomato' in t:
        return False
    if 'beef' not in t:
        return False
    negative = ['broth', 'stock', 'seasoning', 'flavor', 'bouillon', 'soup', 'noodle', 'noodles', 'ramen', 'tomato']
    positives = ['ground', 'steak', 'roast', 'patty', 'ribs', 'sirloin', 'chuck', 'ribeye', 'brisket', 'lean', 'organic', 'fresh', 'boneless', 'bone-in', 'mince', 'minced', 'filet', 'fillet', 'corned']
    if any(n in t for n in negative) and not any(p in t for p in positives):
        return False
    return True

# Prefer cart under initialfinaldiff.added/updated.cart.cartItems if available

def get_preferred_cart_items(data):
    items = []
    try:
        added = data.get('initialfinaldiff', {}).get('added', {})
        updated = data.get('initialfinaldiff', {}).get('updated', {})
        for section in (added, updated):
            cart = section.get('cart', {}) if isinstance(section, dict) else {}
            ci = cart.get('cartItems') if isinstance(cart, dict) else None
            if isinstance(ci, list) and ci:
                items.extend(ci)
        if items:
            return items
    except Exception:
        pass
    # Fallback: collect any cartItems outside deleted
    return collect_cart_items(data, in_deleted=False)


def verify(path):
    # Strategy: find cart items representing final cart; then require at least one chicken item and one beef item by checking item names/descriptions with safeguarding negatives.
    data = load_json(path)
    cart_items = get_preferred_cart_items(data)
    has_chicken = False
    has_beef = False
    for it in cart_items or []:
        if not isinstance(it, dict):
            continue
        name = str(it.get('name', ''))
        desc = str(it.get('description', ''))
        text = (name + ' ' + desc).strip()
        if not text:
            continue
        if is_chicken(text):
            has_chicken = True
        if is_beef(text):
            has_beef = True
        if has_chicken and has_beef:
            break
    return has_chicken and has_beef

if __name__ == '__main__':
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        sys.exit(0)
    result = False
    try:
        result = verify(path)
    except Exception:
        result = False
    print('SUCCESS' if result else 'FAILURE')
