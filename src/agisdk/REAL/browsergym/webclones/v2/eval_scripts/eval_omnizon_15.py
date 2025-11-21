import json
import sys

# Strategy: The task is successful only if a purchase was made and the purchased
# items include a pack of sports balls. From training examples, item id "114"
# corresponds to a sports balls pack. We verify by checking for an added order
# and confirming at least one item in the order has id "114" with quantity > 0.


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def deep_get(d, keys, default=None):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def get_orders(data):
    orders_root = deep_get(data, ["initialfinaldiff", "added", "order", "orders"], None)
    if not isinstance(orders_root, dict):
        return []
    return list(orders_root.values())


def is_sports_balls_item(item):
    # Known sports balls SKU from training data
    sports_ids = {"114"}
    iid = str(item.get("id", "")).strip()
    return iid in sports_ids


def purchased_sports_balls(data):
    orders = get_orders(data)
    for order in orders:
        items = order.get("items", [])
        if not isinstance(items, list):
            continue
        for it in items:
            if not isinstance(it, dict):
                continue
            if is_sports_balls_item(it):
                # Ensure positive quantity when present; default to 1 if missing
                qty = it.get("quantity", 1)
                try:
                    if float(qty) > 0:
                        return True
                except Exception:
                    # If quantity is non-numeric but item matches, consider it purchased
                    return True
    return False


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    data = load_json(path) if path else {}
    if purchased_sports_balls(data):
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
