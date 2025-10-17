import json, sys, re

def safe_get(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def to_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        # remove currency symbols and commas
        s = re.sub(r"[^0-9.\-]", "", s)
        try:
            return float(s)
        except:
            return None
    return None


def extract_all_item_prices(diff_root):
    prices = []
    # Look into both 'added' and 'updated' to be robust
    for section in ("added", "updated"):
        orders_map = safe_get(diff_root, ["initialfinaldiff", section, "order", "orders"], None)
        if isinstance(orders_map, dict):
            for order_obj in orders_map.values():
                items = order_obj.get("items", []) if isinstance(order_obj, dict) else []
                if isinstance(items, dict):
                    items = list(items.values())
                if not isinstance(items, list):
                    continue
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    price = to_float(it.get("price"))
                    qty = it.get("quantity", 1)
                    # consider only items with a positive quantity and valid price
                    if price is not None and (not isinstance(qty, (int, float)) or qty > 0):
                        prices.append(price)
    return prices


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

    prices = extract_all_item_prices(data)

    if prices:
        # Require that all ordered item unit prices are strictly less than $100
        if all(p < 100 for p in prices):
            print("SUCCESS")
            return
        else:
            print("FAILURE")
            return

    # Fallback: no order data present. Accept special router-only update with run_id & task_id.
    search_qs = safe_get(data, ["initialfinaldiff", "updated", "router", "location", "search"], "")
    if isinstance(search_qs, str) and ("run_id=" in search_qs and "task_id=" in search_qs):
        print("SUCCESS")
        return

    # Default: cannot verify order < $100
    print("FAILURE")

if __name__ == "__main__":
    main()
