import json, sys

def extract_cart_items(data):
    # Prefer the standard path used in examples
    try_paths = [
        ['initialfinaldiff', 'added', 'cart', 'cartItems'],
        ['cart', 'cartItems'],
    ]
    for path in try_paths:
        cur = data
        ok = True
        for k in path:
            if isinstance(cur, dict) and k in cur:
                cur = cur[k]
            else:
                ok = False
                break
        if ok and isinstance(cur, list):
            return cur
    # Fallback: recursively search for any 'cartItems' list
    results = []
    def rec(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == 'cartItems' and isinstance(v, list):
                    results.append(v)
                rec(v)
        elif isinstance(obj, list):
            for it in obj:
                rec(it)
    rec(data)
    if results:
        # Pick the longest list assuming it represents the final cart
        results.sort(key=lambda x: len(x), reverse=True)
        return results[0]
    return []


def main():
    # Strategy:
    # - Find cart items. Consider items with quantity >= 2 as an "order".
    # - Accept SUCCESS if there exist at least two different rice dishes (name contains 'rice'),
    #   both with quantity >= 2, and the pair meets one of:
    #     (a) both are fried rice (name contains both 'fried' and 'rice'), or
    #     (b) one is fried rice and the other is a rice dish.
    # This aligns with examples: quantities matter and Example 1 passes with one fried rice + another rice dish.
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    items = extract_cart_items(data)

    qualifying = {}
    for it in items:
        name = ''
        if isinstance(it, dict):
            name = str(it.get('name', '')).strip()
            qty = it.get('quantity', 0)
            try:
                qty = int(qty)
            except Exception:
                # If quantity is not an int, try to parse or default to 0
                try:
                    qty = int(float(qty))
                except Exception:
                    qty = 0
        else:
            continue
        if qty >= 2 and name:
            lname = name.lower()
            is_rice = 'rice' in lname
            is_fried_rice = ('fried' in lname) and is_rice
            # Track the strongest classification seen for a given dish name
            if lname not in qualifying:
                qualifying[lname] = {'is_rice': is_rice, 'is_fried_rice': is_fried_rice}
            else:
                # Upgrade flags if necessary
                qualifying[lname]['is_rice'] = qualifying[lname]['is_rice'] or is_rice
                qualifying[lname]['is_fried_rice'] = qualifying[lname]['is_fried_rice'] or is_fried_rice

    names = list(qualifying.keys())
    # Need at least two different dishes
    success = False
    n = len(names)
    if n >= 2:
        for i in range(n):
            for j in range(i+1, n):
                a = qualifying[names[i]]
                b = qualifying[names[j]]
                # Pair acceptance rules
                both_fried = a['is_fried_rice'] and b['is_fried_rice']
                one_fried_other_rice = (a['is_fried_rice'] and b['is_rice']) or (b['is_fried_rice'] and a['is_rice'])
                if both_fried or one_fried_other_rice:
                    success = True
                    break
            if success:
                break

    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()
