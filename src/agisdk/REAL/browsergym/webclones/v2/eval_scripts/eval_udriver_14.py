import json
import sys

# Task: Verify that the default payment method has been changed to the existing card on file (Visa •••• 4242),
# and that the currently selected payment method matches that same card (not wallet or a newly added card).
# Strategy:
# 1) Locate the pre-existing card on file: assume consistent environment where the original card is Visa ending in 4242.
# 2) Confirm this card is set as default (isDefault True) and ride.selectedPaymentMethod points to this card (type credit and id or displayName match).


def load_json(path):
    with open(path) as f:
        return json.load(f)


def find_card_on_file(payment_methods):
    # Identify the original card on file - Visa ending in 4242 (seen consistently in env)
    candidates = []
    for pm in payment_methods:
        if pm and isinstance(pm, dict):
            if str(pm.get("type")) == "credit" and str(pm.get("last4")) == "4242":
                candidates.append(pm)
    if not candidates:
        # Fallback: try id == '1' when last4 not detectable (environment-specific)
        for pm in payment_methods:
            if (
                pm
                and isinstance(pm, dict)
                and str(pm.get("type")) == "credit"
                and str(pm.get("id")) == "1"
            ):
                candidates.append(pm)
    # Prefer id == '1' among candidates if present for stability
    for pm in candidates:
        if str(pm.get("id")) == "1":
            return pm
    return candidates[0] if candidates else None


def selected_matches_card(selected, card):
    if not selected or not isinstance(selected, dict) or not card:
        return False
    if str(selected.get("type")) != "credit":
        return False
    sel_id = str(selected.get("id")) if selected.get("id") is not None else None
    card_id = str(card.get("id")) if card.get("id") is not None else None
    if sel_id and card_id and sel_id == card_id:
        return True
    # Fallback using displayName last4 if IDs are missing/mismatch
    disp = selected.get("displayName")
    if isinstance(disp, str) and disp.strip().endswith("4242"):
        return True
    return False


def main():
    try:
        path = sys.argv[1]
        data = load_json(path)
        added = data.get("initialfinaldiff", {}).get("added", {})
        user = added.get("user", {})
        ride = added.get("ride", {})
        wallet = user.get("wallet", {})
        payment_methods = wallet.get("paymentMethods", [])

        # Find the original card on file
        card_on_file = find_card_on_file(payment_methods)
        if not card_on_file:
            print("FAILURE")
            return

        # Check that this card is set as default
        if not bool(card_on_file.get("isDefault")):
            print("FAILURE")
            return

        # Verify the selected payment method matches the card on file
        selected = ride.get("selectedPaymentMethod", {})
        if not selected_matches_card(selected, card_on_file):
            print("FAILURE")
            return

        print("SUCCESS")
    except Exception:
        # On any parsing/runtime error, mark as failure to avoid false positives
        print("FAILURE")


if __name__ == "__main__":
    main()
