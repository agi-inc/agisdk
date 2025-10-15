import sys, json

# Task: Verify that a coffee maker/machine was ordered successfully.
# Strategy:
# 1) Confirm purchase completion by checking if the final route is the confirmation page.
# 2) Extract purchased items from order data; if absent, fall back to cart details, then miniCart justAdded.
# 3) Succeed only if exactly one unit was purchased and its product ID matches known coffee maker IDs.


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_path(data):
    try:
        return (
            data.get('initialfinaldiff', {})
                .get('updated', {})
                .get('router', {})
                .get('location', {})
                .get('pathname')
        )
    except Exception:
        return None


def get_order_items(data):
    items = []
    added = data.get('initialfinaldiff', {}).get('added', {})
    # Primary: order items
    orders = added.get('order', {}).get('orders', {})
    if isinstance(orders, dict) and orders:
        for order_obj in orders.values():
            its = order_obj.get('items')
            if isinstance(its, list):
                for it in its:
                    if isinstance(it, dict):
                        iid = it.get('id')
                        qty = it.get('quantity', 1)
                        if iid is not None:
                            items.append({'id': str(iid), 'quantity': int(qty) if isinstance(qty, (int, float)) else 1})
        if items:
            return items
    # Fallback: cart details (if we reached confirmation but order object wasn't captured in diff)
    cart_details = added.get('cart', {}).get('cartDetails', {})
    if isinstance(cart_details, dict) and cart_details:
        for v in cart_details.values():
            if isinstance(v, dict):
                iid = v.get('id')
                qty = v.get('quantity', 1)
                if iid is not None:
                    items.append({'id': str(iid), 'quantity': int(qty) if isinstance(qty, (int, float)) else 1})
        if items:
            return items
    # Last resort: miniCart justAdded (assume quantity 1)
    just_added = (
        data.get('initialfinaldiff', {})
            .get('updated', {})
            .get('ui', {})
            .get('miniCart', {})
            .get('justAdded')
    )
    if just_added is not None:
        items.append({'id': str(just_added), 'quantity': 1})
    return items


def main():
    path = sys.argv[1]
    data = load_json(path)

    pathname = get_path(data)
    purchase_confirmed = (pathname == '/confirmation')
    if not purchase_confirmed:
        print('FAILURE')
        return

    items = get_order_items(data)

    # Filter items with positive quantity
    valid_items = []
    total_qty = 0
    for it in items:
        try:
            q = int(it.get('quantity', 1))
        except Exception:
            q = 1
        if q > 0:
            valid_items.append({'id': str(it.get('id')), 'quantity': q})
            total_qty += q

    # Must purchase exactly one unit
    if total_qty != 1 or len(valid_items) != 1:
        print('FAILURE')
        return

    # Known coffee maker/machine product IDs inferred from training successes
    coffee_maker_ids = {'176', '177', '180', '183'}

    sole_item_id = valid_items[0]['id']
    if sole_item_id in coffee_maker_ids:
        print('SUCCESS')
    else:
        print('FAILURE')


if __name__ == '__main__':
    main()
