import sys, json

# Strategy:
# - Confirm navigation reached the confirmation page and an order was added.
# - Ensure the search intent targeted 'headphones' (case-insensitive, substring 'headphone').
# - Validate at least one ordered item's price is strictly >24 and <100.
# - Disqualify if search terms indicate non-headphone items (e.g., keyboard, earbuds).


def safe_get(d, path, default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    try:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diff = data.get("initialfinaldiff", {}) or {}
    added = diff.get("added", {}) or {}
    updated = diff.get("updated", {}) or {}

    # Check confirmation page
    pathname = safe_get(updated, ["router", "location", "pathname"], "")
    is_confirmation = isinstance(pathname, str) and pathname.endswith("/confirmation")

    # Collect search intent strings
    filter_obj = updated.get("filter", {}) or {}
    search_parts = []
    for k in ("searchQuery", "searchInputValue"):
        v = filter_obj.get(k)
        if isinstance(v, str):
            search_parts.append(v.lower())
    search_text = " ".join(search_parts)

    # Determine if the user specifically searched for headphones
    has_headphones_intent = "headphone" in search_text  # matches headphone/headphones

    # Disqualify obvious non-headphone intents
    bad_keywords = [
        "keyboard", "gaming keyboard", "earbud", "earbuds", "ear pod", "earpod",
        "earpods", "earphone", "earphones"
    ]
    if any(bad in search_text for bad in bad_keywords):
        has_headphones_intent = False

    # Extract ordered item prices
    orders = safe_get(added, ["order", "orders"], {})
    prices = []
    if isinstance(orders, dict):
        for _, order in orders.items():
            if isinstance(order, dict):
                items = order.get("items", [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            price = item.get("price")
                            if isinstance(price, (int, float)):
                                try:
                                    prices.append(float(price))
                                except Exception:
                                    pass

    has_order = len(prices) > 0

    # Price validation: at least one item in the valid range
    price_ok = any(24 < p < 100 for p in prices)

    success = is_confirmation and has_order and price_ok and has_headphones_intent

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
