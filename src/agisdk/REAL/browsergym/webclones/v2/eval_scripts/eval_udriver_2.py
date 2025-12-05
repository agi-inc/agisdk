import json
import sys

# Verification script for: Add $100 of UDriver credits to balance using the card on account
# Strategy:
# 1) Robustly find the wallet object by recursively traversing the JSON (handles varied nesting under added/updated).
# 2) Validate exactly one transaction: description == "Wallet Top-up", type == "credit", amount == 100.
# 3) Validate final balance equals 125.5 (baseline 25.5 + 100) and that at least one credit card exists in paymentMethods.
# Print only SUCCESS or FAILURE.


def to_number(x):
    try:
        return float(x)
    except Exception:
        return None


def find_wallet(node):
    # Recursively search for a dict that looks like a wallet
    if isinstance(node, dict):
        # Heuristic: must have balance (number) and transactions (list)
        if (
            "balance" in node
            and "transactions" in node
            and isinstance(node.get("transactions"), list)
        ):
            bal = to_number(node.get("balance"))
            if bal is not None:
                return node
        # Recurse into values
        for v in node.values():
            res = find_wallet(v)
            if res is not None:
                return res
    elif isinstance(node, list):
        for item in node:
            res = find_wallet(item)
            if res is not None:
                return res
    return None


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    wallet = None
    # Prefer searching under initialfinaldiff.added first for efficiency/precision, then fallback to full JSON
    cur = data
    for key in ["initialfinaldiff", "added", "user", "wallet"]:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            cur = None
            break
    if isinstance(cur, dict) and "balance" in cur and "transactions" in cur:
        wallet = cur
    else:
        # Try updated path
        cur = data
        for key in ["initialfinaldiff", "updated", "user", "wallet"]:
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                cur = None
                break
        if isinstance(cur, dict) and "balance" in cur and "transactions" in cur:
            wallet = cur
        else:
            # Fallback: recursive search
            wallet = find_wallet(data)

    if not isinstance(wallet, dict):
        print("FAILURE")
        return

    balance = to_number(wallet.get("balance"))
    transactions = (
        wallet.get("transactions") if isinstance(wallet.get("transactions"), list) else []
    )
    pm = wallet.get("paymentMethods") if isinstance(wallet.get("paymentMethods"), list) else []

    # Count 100$ credit top-ups
    count_100_credit = 0
    for t in transactions:
        if not isinstance(t, dict):
            continue
        desc = t.get("description")
        amt = to_number(t.get("amount"))
        ttype = t.get("type")
        if (
            desc == "Wallet Top-up"
            and ttype == "credit"
            and amt is not None
            and abs(amt - 100.0) < 1e-9
        ):
            count_100_credit += 1

    # Ensure a credit card exists (reflects "using the card on my account")
    has_credit_card = any(isinstance(m, dict) and m.get("type") == "credit" for m in pm)

    success = (
        balance is not None
        and abs(balance - 125.5) < 1e-9
        and count_100_credit == 1
        and has_credit_card
    )

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
