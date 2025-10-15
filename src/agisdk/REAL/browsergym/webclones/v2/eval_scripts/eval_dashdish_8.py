# Task: DashDish - Verify an order for any type of sub-sandwich was placed and total < $30
# Strategy:
# 1) Confirm there is at least one cart item whose name contains "sub" or "sandwich" (case-insensitive).
# 2) Ensure checkout totalAmount exists, is > 0, and strictly < 30. If any condition fails -> FAILURE.

import json
import sys

def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    # Navigate to cart data
    cart = safe_get(data, ["initialfinaldiff", "added", "cart"], {}) or {}
    cart_items = cart.get("cartItems")
    if not isinstance(cart_items, list) or len(cart_items) == 0:
        print("FAILURE")
        sys.exit(0)

    # Identify presence of a sub-sandwich by item name
    has_sub = False
    for item in cart_items:
        name = ""
        if isinstance(item, dict):
            name = str(item.get("name", ""))
        lname = name.lower()
        # Accept either 'sub' or 'sandwich' anywhere in the name
        if ("sub" in lname) or ("sandwich" in lname):
            has_sub = True
            break

    if not has_sub:
        # No qualifying sub-sandwich in the order
        print("FAILURE")
        sys.exit(0)

    # Validate total amount constraints
    total_amount = safe_get(cart, ["checkoutDetails", "charges", "totalAmount"], None)
    try:
        total_val = float(total_amount)
    except (TypeError, ValueError):
        print("FAILURE")
        sys.exit(0)

    # Must be an actual placed order: total > 0 and strictly under $30
    if total_val <= 0:
        print("FAILURE")
        sys.exit(0)

    if not (total_val < 30.0):
        print("FAILURE")
        sys.exit(0)

    print("SUCCESS")
except Exception:
    # Any unexpected issue -> FAILURE to avoid false positives
    print("FAILURE")