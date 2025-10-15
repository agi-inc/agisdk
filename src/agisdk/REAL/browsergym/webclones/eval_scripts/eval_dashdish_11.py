import json, sys

# Verification script for task: "Order me 2 different type of Tacos."
# Strategy:
# 1) Recursively collect all cartItems from the final_state_diff JSON (handles added/updated paths).
# 2) Identify items whose name contains "taco" (case-insensitive).
# 3) Normalize names by removing parentheses content and the word "taco(s)" to infer the base type.
# 4) Count unique base types; SUCCESS if at least two different taco types are present, else FAILURE.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_cart_items(obj):
    items = []
    # Recursive search for any key named 'cartItems'
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == 'cartItems' and isinstance(v, list):
                for el in v:
                    if isinstance(el, dict):
                        items.append(el)
            else:
                items.extend(extract_cart_items(v))
    elif isinstance(obj, list):
        for el in obj:
            items.extend(extract_cart_items(el))
    return items


def strip_parentheses(s):
    # Remove any content inside parentheses without using regex
    out = []
    depth = 0
    for ch in s:
        if ch == '(':
            depth += 1
            continue
        if ch == ')':
            if depth > 0:
                depth -= 1
            continue
        if depth == 0:
            out.append(ch)
    return ''.join(out)


def normalize_type(name):
    # Lowercase, remove parentheses content, keep letters/spaces, remove tokens 'taco'/'tacos'
    if not name:
        return ''
    s = name.lower()
    s = strip_parentheses(s)
    # Keep only letters and spaces
    cleaned_chars = []
    for ch in s:
        if 'a' <= ch <= 'z' or ch == ' ':
            cleaned_chars.append(ch)
        else:
            cleaned_chars.append(' ')
    s = ''.join(cleaned_chars)
    tokens = [t for t in s.split() if t]
    tokens = [t for t in tokens if t not in ('taco', 'tacos')]
    # Collapse back
    base = ' '.join(tokens).strip()
    if not base:
        # fallback to original lowercased name without extra spaces
        base = ' '.join([t for t in name.lower().split() if t])
    return base


def main():
    path = sys.argv[1]
    data = load_json(path)

    cart_items = extract_cart_items(data)

    # Deduplicate by uniqueIdentifier if present, else by (id,name,size,preferences)
    seen = set()
    deduped = []
    for it in cart_items:
        key = None
        if isinstance(it, dict):
            uid = it.get('uniqueIdentifier')
            if uid:
                key = ('uid', uid)
            else:
                key = (
                    'fallback',
                    str(it.get('id', '')),
                    str(it.get('name', '')),
                    str(it.get('size', '')),
                    str(it.get('preferences', '')),
                )
        if key and key not in seen:
            seen.add(key)
            deduped.append(it)

    # Filter taco items
    taco_items = []
    for it in deduped:
        name = str(it.get('name', ''))
        if name and ('taco' in name.lower()):
            taco_items.append(it)

    # Compute unique types
    unique_types = set()
    for it in taco_items:
        base_type = normalize_type(it.get('name', ''))
        if base_type:
            unique_types.add(base_type)

    if len(unique_types) >= 2:
        print('SUCCESS')
    else:
        print('FAILURE')


if __name__ == '__main__':
    main()
