import sys, json

# Strategy:
# 1) SUCCESS if a confirmed booking exists with a stay title containing "oceanfront" (case-insensitive)
#    and the reservation is exactly one night (checkout is the day after checkin).
# 2) If no bookingDetails, consider SUCCESS if booking form reached and only ZIP code error is present
#    (zipcode error non-empty while other payment errors empty). Else FAILURE.

def get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def is_oceanfront(title: str) -> bool:
    if not isinstance(title, str):
        return False
    t = title.lower()
    # Allow common variants
    keywords = ["oceanfront", "ocean front"]
    return any(k in t for k in keywords)


def parse_iso_date(iso_str):
    # Expect formats like 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS.sssZ'
    if not isinstance(iso_str, str) or len(iso_str) < 10:
        return None
    try:
        date_part = iso_str.split('T')[0]
        y, m, d = date_part.split('-')
        return int(y), int(m), int(d)
    except Exception:
        return None


def is_leap(year):
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def date_to_ordinal(y, m, d):
    # Compute days before this year
    y_prev = y - 1
    leaps = y_prev // 4 - y_prev // 100 + y_prev // 400
    days_before_year = y_prev * 365 + leaps
    mdays = [31, 28 + (1 if is_leap(y) else 0), 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # days before this month
    days_before_month = sum(mdays[:max(0, m-1)])
    return days_before_year + days_before_month + d


def one_night(checkin, checkout):
    ci = parse_iso_date(checkin)
    co = parse_iso_date(checkout)
    if not ci or not co:
        return False
    try:
        ci_ord = date_to_ordinal(*ci)
        co_ord = date_to_ordinal(*co)
        return (co_ord - ci_ord) == 1
    except Exception:
        return False


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

    added = get(data, ["initialfinaldiff", "added"], {}) or {}
    booking = added.get("booking", {}) or {}

    # 1) Check confirmed booking details for oceanfront and one-night
    details = booking.get("bookingDetails")
    success = False
    if isinstance(details, dict) and details:
        for _, res in details.items():
            if not isinstance(res, dict):
                continue
            stay = res.get("stay", {}) or {}
            title = stay.get("title", "")
            checkin = res.get("checkin")
            checkout = res.get("checkout")
            if is_oceanfront(title) and one_night(checkin, checkout):
                success = True
                break
        if success:
            print("SUCCESS")
            return
        else:
            # Booking exists but does not meet oceanfront/one-night criteria
            print("FAILURE")
            return

    # 2) Fallback: consider partial booking success if only ZIP code error present
    errors = booking.get("errors", {}) or {}
    zipcode_err = errors.get("zipcode")
    card_err = errors.get("cardNumber")
    exp_err = errors.get("expiration")
    cvv_err = errors.get("cvv")

    if (isinstance(zipcode_err, str) and zipcode_err.strip() != "") \
       and (not card_err) and (not exp_err) and (not cvv_err):
        print("SUCCESS")
        return

    # Otherwise failure
    print("FAILURE")

if __name__ == "__main__":
    main()
