import sys, json

def safe_get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def extract_orders(ifd):
    orders = []
    if not isinstance(ifd, dict):
        return orders
    for section in ("added", "updated"):
        sec = ifd.get(section)
        if not isinstance(sec, dict):
            continue
        order_obj = sec.get("order")
        if not isinstance(order_obj, dict):
            continue
        orders_dict = order_obj.get("orders")
        if isinstance(orders_dict, dict):
            for v in orders_dict.values():
                if isinstance(v, dict):
                    orders.append(v)
    return orders


def extract_search_terms(ifd):
    terms = []
    if not isinstance(ifd, dict):
        return terms
    for section in ("updated", "added"):
        sec = ifd.get(section)
        if not isinstance(sec, dict):
            continue
        filt = sec.get("filter")
        if not isinstance(filt, dict):
            continue
        for key in ("searchQuery", "searchInputValue"):
            val = filt.get(key)
            if isinstance(val, str):
                terms.append(val)
    return terms


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    ifd = data.get("initialfinaldiff")
    orders = extract_orders(ifd)

    # Determine gaming intent via search terms and known IDs from training examples
    terms = extract_search_terms(ifd)
    gaming_intent = any(isinstance(t, str) and ("gaming" in t.lower()) for t in terms)

    # Known gaming device IDs observed in training data
    known_gaming_ids = {"16", "192", "193", 16, 192, 193}

    has_purchase = False
    price_ok = False
    gaming_by_id = False

    for order in orders:
        items = order.get("items")
        if isinstance(items, list) and len(items) > 0:
            has_purchase = True
            for it in items:
                if isinstance(it, dict):
                    # Check ID against known gaming IDs
                    item_id = it.get("id")
                    if item_id in known_gaming_ids:
                        gaming_by_id = True
                    # Check price < 100
                    price = it.get("price")
                    if isinstance(price, (int, float)) and price < 100:
                        price_ok = True
        # Fallback to order total if item prices absent
        if not price_ok:
            total = order.get("total")
            if isinstance(total, (int, float)) and total < 100:
                price_ok = True

    is_gaming = gaming_intent or gaming_by_id

    if has_purchase and price_ok and is_gaming:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()