import json, sys

# Verifier for: "Staynb: Find me a place to stay for 1 night Aug 17 under $450"
# Strategy:
# 1) Confirm a reservation exists with checkin 2024-08-17 and checkout 2024-08-18 (1 night).
# 2) Validate the price constraint conservatively by applying a 12% fee/tax to nightly price and ensure total < 450.
#    This aligns with cases where the base nightly price alone might be under $450 but total exceeds it.


def safe_get(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def parse_date(s):
    # Expecting ISO like 2024-08-17T00:00:00.000Z; return date part 'YYYY-MM-DD'
    if not isinstance(s, str):
        return None
    # Extract first 10 chars if well-formed
    if len(s) >= 10:
        return s[:10]
    return None


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Navigate to bookingDetails within initialfinaldiff.added.booking.bookingDetails
    added = safe_get(data, ["initialfinaldiff", "added"], {}) or {}
    booking_root = added.get("booking", {}) if isinstance(added, dict) else {}
    booking_details = booking_root.get("bookingDetails")

    # If bookingDetails missing or empty -> failure
    if not isinstance(booking_details, dict) or len(booking_details) == 0:
        print("FAILURE")
        return

    TARGET_CHECKIN = "2024-08-17"
    TARGET_CHECKOUT = "2024-08-18"
    MAX_TOTAL = 450
    FEE_MULTIPLIER = 1.12  # conservative estimate to align with observed feedback

    success = False

    for key, bd in booking_details.items():
        if not isinstance(bd, dict):
            continue
        checkin = parse_date(bd.get("checkin"))
        checkout = parse_date(bd.get("checkout"))
        if checkin != TARGET_CHECKIN or checkout != TARGET_CHECKOUT:
            continue
        # optional guest sanity: at least 1 adult
        guests = bd.get("guests") or {}
        adults = guests.get("Adults") if isinstance(guests, dict) else None
        if adults is None:
            adults_ok = True  # be permissive if field missing
        else:
            try:
                adults_ok = int(adults) >= 1
            except Exception:
                adults_ok = True
        if not adults_ok:
            continue
        # price check
        stay = bd.get("stay") or {}
        price = stay.get("price")
        try:
            price_val = float(price)
        except Exception:
            # If price missing, cannot verify under-budget; treat as failure for this record
            continue
        total_estimated = price_val * FEE_MULTIPLIER
        if total_estimated < MAX_TOTAL:
            success = True
            break

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
