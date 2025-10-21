import json, sys

# Task: Verify that exactly 2 speakers under $50 each were ordered.
# Strategy:
# 1) Locate the most recent order in added.order.orders and extract items.
# 2) Confirm total quantity == 2, all items are known speakers, and each unit price < 50.

SPEAKER_IDS = {"128", "130", "206"}  # Known speaker IDs from site dataset inferred from training states

def to_float(x):
    try:
        return float(x)
    except Exception:
        return None

def get_latest_order(orders_dict):
    latest = None
    best_date = ""
    # orders_dict keys are like "0", "1", ... values are order objects
    for _, order in orders_dict.items():
        d = order.get("date")
        if isinstance(d, str):
            if d > best_date:
                best_date = d
                latest = order
    if latest is None:
        # fallback: first one
        for _, order in orders_dict.items():
            latest = order
            break
    return latest


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    root = data.get('initialfinaldiff') or data
    added = root.get('added') or {}
    order_root = (added.get('order') or {})
    orders_dict = order_root.get('orders') or {}

    if not isinstance(orders_dict, dict) or not orders_dict:
        print("FAILURE")
        return

    order = get_latest_order(orders_dict)
    if not isinstance(order, dict):
        print("FAILURE")
        return

    items = order.get('items') or []
    if not isinstance(items, list) or len(items) == 0:
        print("FAILURE")
        return

    total_qty = 0
    all_known_speakers = True
    all_prices_under_50 = True

    for it in items:
        if not isinstance(it, dict):
            print("FAILURE")
            return
        id_raw = it.get('id')
        q = it.get('quantity')
        p = to_float(it.get('price'))

        # Validate presence and types
        try:
            q = int(q)
        except Exception:
            print("FAILURE")
            return
        if p is None:
            print("FAILURE")
            return

        total_qty += q
        id_str = str(id_raw) if id_raw is not None else None
        if id_str is None or id_str not in SPEAKER_IDS:
            all_known_speakers = False
        if not (p < 50):
            all_prices_under_50 = False

    if total_qty == 2 and all_known_speakers and all_prices_under_50:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
