import json, sys

# Strategy:
# - Load final_state_diff.json and extract cart details from initialfinaldiff.added/updated.cart
# - Success if ALL are true:
#     1) At least one cart item name indicates BBQ Wings (name contains 'bbq'/'barbecue' and 'wing')
#     2) Shipping option is Delivery and delivery option is Express
#     3) Tip equals 4.00 (numeric compare with tolerance)
# - Be defensive: handle missing keys, different types (str/number), and case-insensitive comparisons

def get_nested(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur

def parse_float(val):
    try:
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            return float(val.strip())
    except Exception:
        return None
    return None

def is_bbq_wings(name):
    if not isinstance(name, str):
        return False
    s = name.lower()
    has_bbq = ('bbq' in s) or ('barbecue' in s) or ('barbeque' in s)
    has_wing = ('wing' in s)  # matches 'wing' and 'wings'
    return has_bbq and has_wing


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Try to locate the cart under added first, then updated
    cart = get_nested(data, ["initialfinaldiff", "added", "cart"]) or \
           get_nested(data, ["initialfinaldiff", "updated", "cart"]) or {}

    cart_items = cart.get("cartItems")
    if not isinstance(cart_items, list):
        cart_items = []

    bbq_item_present = any(is_bbq_wings(item.get("name", "")) for item in cart_items)

    checkout = cart.get("checkoutDetails", {})
    shipping = checkout.get("shipping", {}) if isinstance(checkout, dict) else {}
    charges = checkout.get("charges", {}) if isinstance(checkout, dict) else {}

    shipping_option = str(shipping.get("shippingOption", "")).strip().lower()
    delivery_option = str(shipping.get("deliveryOption", "")).strip().lower()

    tip_val = parse_float(charges.get("tip"))

    # Conditions
    cond_item = bbq_item_present
    cond_shipping = (shipping_option == "delivery") and (delivery_option == "express")
    cond_tip = (tip_val is not None) and (abs(tip_val - 4.0) < 1e-6)

    if cond_item and cond_shipping and cond_tip:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
