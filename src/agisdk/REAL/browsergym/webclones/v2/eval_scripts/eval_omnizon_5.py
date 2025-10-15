import json, sys

# Strategy inside code:
# - Load final_state_diff.json, locate the latest placed order from added.order.orders
# - Confirm navigation to /confirmation, search query indicates coffee, and at least one ordered item has price <= 100
# - Print SUCCESS if all conditions met, else FAILURE

def safe_get(d, *keys):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return None
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)
except Exception:
    print("FAILURE")
    sys.exit(0)

initialfinaldiff = data.get('initialfinaldiff') or {}
added = initialfinaldiff.get('added') or {}
updated = initialfinaldiff.get('updated') or {}

orders_dict = safe_get(added, 'order', 'orders')
if not isinstance(orders_dict, dict) or not orders_dict:
    print("FAILURE")
    sys.exit(0)

# Choose latest order by date if available
latest_order = None
latest_ts = None
for ord_k, ord_v in orders_dict.items():
    if not isinstance(ord_v, dict):
        continue
    date_str = ord_v.get('date')
    ts_val = None
    if isinstance(date_str, str):
        # crude parse: ISO with 'Z' -> +00:00, compare lexicographically or fallback
        # We'll use lexicographic as ISO-8601 is sortable
        ts_val = date_str
    if latest_order is None or (ts_val is not None and (latest_ts is None or ts_val > latest_ts)):
        latest_order = ord_v
        latest_ts = ts_val

if not latest_order:
    print("FAILURE")
    sys.exit(0)

items = latest_order.get('items') or []
# Ensure items is a list of dicts with price
any_under_100 = False
for it in items:
    if isinstance(it, dict):
        price = it.get('price')
        try:
            if price is not None and float(price) <= 100:
                any_under_100 = True
                break
        except Exception:
            pass

# Check confirmation page
pathname = safe_get(updated, 'router', 'location', 'pathname') or ''
on_confirmation = pathname == '/confirmation'

# Check that the user searched for coffee (proxy for coffee maker)
filter_block = safe_get(updated, 'filter') or {}
q_parts = []
for k in ('searchQuery', 'searchInputValue'):
    v = filter_block.get(k)
    if isinstance(v, str):
        q_parts.append(v)
q_text = ' '.join(q_parts).lower()
has_coffee_query = ('coffee' in q_text)

# Final decision
if on_confirmation and has_coffee_query and any_under_100:
    print("SUCCESS")
else:
    print("FAILURE")
