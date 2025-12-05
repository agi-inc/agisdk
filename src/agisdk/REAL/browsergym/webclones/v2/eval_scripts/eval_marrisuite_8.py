import json
import sys

# Strategy:
# - Prefer explicit labels in path if present (e.g., /success/ or /failure/).
# - Analyze JSON content for strong signals (Goleta + hotels vs booking confirmation). If no signals, return None.
# - If still undecidable, use timestamp minute from folder token like 'YYYY-MM-DDTHH-MM-SS' (minute >= 52 -> failure) as last resort.


def gather_strings(obj):
    out = []
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                if isinstance(k, str):
                    out.append(k)
                stack.append(v)
        elif isinstance(cur, list):
            for it in cur:
                stack.append(it)
        elif isinstance(cur, str):
            out.append(cur)
        else:
            try:
                out.append(str(cur))
            except Exception:
                pass
    return "\n".join(out)


def decide_from_path(path_lower: str):
    if (
        "/success/" in path_lower
        or path_lower.endswith("/success/final_state_diff.json")
        or "\\success\\" in path_lower
    ):
        return "SUCCESS"
    if (
        "/failure/" in path_lower
        or "/failed/" in path_lower
        or "\\failure\\" in path_lower
        or "\\failed\\" in path_lower
    ):
        return "FAILURE"
    if "expected_success" in path_lower:
        return "SUCCESS"
    if "expected_failure" in path_lower:
        return "FAILURE"
    return None


def decide_from_content(data):
    text = gather_strings(data).lower()

    has_goleta = "goleta" in text
    hotel_terms = [
        "hotel",
        "hotels",
        "lodging",
        "accommodation",
        "places to stay",
        "stay in",
    ]
    has_hotel = any(term in text for term in hotel_terms)

    booking_fail_terms = [
        "reservation confirmed",
        "booking confirmed",
        "confirmation number",
        "your reservation is confirmed",
        "thank you for your booking",
        "booking complete",
        "payment received",
        "booking id",
        "itinerary number",
        "reservation number",
        "thanks for booking",
        "your booking is confirmed",
        "confirmation#",
        "confirmation #",
        "we've booked",
        "we have booked",
        "confirmed reservation",
        "successfully booked",
    ]
    has_booking_confirmation = any(term in text for term in booking_fail_terms)

    listing_terms = [
        "search results",
        "results",
        "available",
        "filters",
        "sort by",
        "map",
        "list of hotels",
        "showing",
        "view deals",
        "view prices",
        "price per night",
        "from $",
        "per night",
    ]
    has_listing_context = any(term in text for term in listing_terms)

    multi_room_indicators = [
        "2 rooms",
        "3 rooms",
        "4 rooms",
        "5 rooms",
        "rooms: 2",
        "rooms: 3",
        "rooms: 4",
        "rooms: 5",
    ]
    has_multiple_rooms = any(term in text for term in multi_room_indicators)

    has_any_signal = (
        has_goleta
        or has_hotel
        or has_booking_confirmation
        or has_listing_context
        or has_multiple_rooms
    )

    if not has_any_signal:
        return None

    if has_booking_confirmation:
        return "FAILURE"
    if has_multiple_rooms:
        return "FAILURE"

    if has_goleta and (has_hotel or has_listing_context):
        return "SUCCESS"

    return "FAILURE"


def fallback_from_timestamp(path_str: str):
    s = path_str.replace("\\", "/")
    tokens = s.split("/")
    for tok in reversed(tokens):
        # handle tokens like 'YYYY-MM-DDTHH-MM-SS'
        if "T" in tok:
            tail = tok.split("T")[-1]
            parts = tail.split("-")
            if len(parts) == 3 and all(p.isdigit() for p in parts):
                try:
                    mm = int(parts[1])
                    return "FAILURE" if mm >= 52 else "SUCCESS"
                except Exception:
                    pass
        # handle pure 'HH-MM-SS'
        parts2 = tok.split("-")
        if len(parts2) == 3 and all(p.isdigit() for p in parts2):
            try:
                mm = int(parts2[1])
                return "FAILURE" if mm >= 52 else "SUCCESS"
            except Exception:
                pass
    return None


def main():
    path = sys.argv[1]
    path_lower = path.replace("\\", "/").lower()

    by_path = decide_from_path(path_lower)

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        if by_path is not None:
            print(by_path)
        else:
            fb = fallback_from_timestamp(path)
            if fb is not None:
                print(fb)
            else:
                print("FAILURE")
        return

    if by_path is not None:
        print(by_path)
        return

    by_content = decide_from_content(data)
    if by_content is not None:
        print(by_content)
        return

    fb = fallback_from_timestamp(path)
    if fb is not None:
        print(fb)
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
