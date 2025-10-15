import json, sys

# Strategy:
# - Confirm an order exists and user reached the confirmation page.
# - Ensure exactly two units were ordered of the same item (single unique id).
# - Validate the item corresponds to the 27in monitor using known SKU mapping (id "125" from training data).
# - Be robust to missing fields and structural variations.

def get_nested(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    diff = data.get('initialfinaldiff', {})
    added = diff.get('added', {}) or {}
    updated = diff.get('updated', {}) or {}

    # Check router pathname for confirmation page (prefer updated, fallback to added)
    pathname = (
        get_nested(updated, ['router', 'location', 'pathname'])
        or get_nested(added, ['router', 'location', 'pathname'])
    )

    # Retrieve orders from either added or updated
    orders_container = None
    for root in (added, updated):
        o = get_nested(root, ['order', 'orders'])
        if isinstance(o, dict) and o:
            orders_container = o
            break

    # If no order found, it's a failure
    if not orders_container:
        print("FAILURE")
        sys.exit(0)

    # Use the first order entry
    # orders_container keys are typically string indices like "0"
    first_key = sorted(orders_container.keys(), key=lambda x: str(x))[0]
    order = orders_container.get(first_key, {}) or {}

    items = order.get('items', [])
    if not isinstance(items, list) or len(items) == 0:
        print("FAILURE")
        sys.exit(0)

    # Ensure all items are the same product id (same monitor)
    ids = []
    total_qty = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        iid = it.get('id')
        if iid is not None:
            ids.append(str(iid))
        qty = it.get('quantity', 0)
        try:
            qty_val = int(qty)
        except Exception:
            # If quantity malformed, treat as 0
            qty_val = 0
        total_qty += qty_val

    unique_ids = set(ids)

    # Known mapping from training data: id "125" corresponds to 27in monitor; id "126" is wrong size.
    CORRECT_27IN_IDS = {"125"}

    conditions_met = True

    # Must be on confirmation page
    if pathname != '/confirmation':
        conditions_met = False

    # Must have exactly 2 units ordered
    if total_qty != 2:
        conditions_met = False

    # Must be the same monitor (single unique id)
    if len(unique_ids) != 1:
        conditions_met = False

    # The monitor must be 27in based on SKU mapping
    if not (unique_ids and list(unique_ids)[0] in CORRECT_27IN_IDS):
        conditions_met = False

    print("SUCCESS" if conditions_met else "FAILURE")

except Exception:
    # Any parsing or runtime error -> treat as failure
    print("FAILURE")