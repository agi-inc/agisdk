import json
import sys


def get_booking_obj(data):
    init_final = data.get("initialfinaldiff", {})
    for section in ["added", "updated"]:
        if isinstance(init_final.get(section), dict) and "booking" in init_final[section]:
            return init_final[section]["booking"]
    for _k, v in init_final.items():
        if isinstance(v, dict) and "booking" in v:
            return v["booking"]
    return None


def is_embarcadero_restaurant(rest):
    if not isinstance(rest, dict):
        return False
    name = (rest.get("name") or "").strip()
    desc = (rest.get("description") or "").strip()
    img = (rest.get("imageUrl") or "").strip()
    text = " ".join([name, desc, img]).lower()

    # Keywords indicative of Embarcadero/waterfront area (avoid overly generic substrings like 'port')
    keywords = [
        "embarcadero",
        "pier",
        "bay",
        "waterfront",
        "harbor",
        "harbour",
        "river",
        "marina",
        "seaside",
        "ferry",
        "wharf",
        "boardwalk",
        "quay",
        "shore",
    ]
    if any(kw in text for kw in keywords):
        return True

    whitelist = {"river view café", "river view cafe", "crowded corner"}
    if name.lower() in whitelist:
        return True

    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    booking = get_booking_obj(data)
    if not isinstance(booking, dict):
        print("FAILURE")
        return

    booking_details = booking.get("bookingDetails")
    if not isinstance(booking_details, dict) or not booking_details:
        print("FAILURE")
        return

    for _, detail in booking_details.items():
        if not isinstance(detail, dict):
            continue
        rest = detail.get("restaurant")
        time = detail.get("time")
        if isinstance(rest, dict) and time:
            if is_embarcadero_restaurant(rest):
                print("SUCCESS")
                return

    print("FAILURE")


if __name__ == "__main__":
    main()
