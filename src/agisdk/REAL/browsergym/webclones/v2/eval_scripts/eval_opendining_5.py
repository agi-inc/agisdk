import json, sys

def normalize_name(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = name.strip().lower()
    # Basic accent normalization for common chars seen
    replacements = {
        "é": "e", "á": "a", "í": "i", "ó": "o", "ú": "u", "ü": "u",
        "’": "'",
    }
    for k, v in replacements.items():
        name = name.replace(k, v)
    return name

# Strategy in code:
# - Load final_state_diff.json and locate booking.bookingDetails.
# - Confirm a concrete reservation: at least one detail with non-null date and time.
# - Validate constraints: restaurant located in Embarcadero (by known IDs or names from training) and rating > 3.0.
# - If any booking detail satisfies all, print SUCCESS; else FAILURE.

def main():
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    booking = (
        data.get('initialfinaldiff', {})
            .get('added', {})
            .get('booking')
    )

    if not isinstance(booking, dict):
        print("FAILURE")
        return

    details = booking.get('bookingDetails')
    if not isinstance(details, dict) or not details:
        # No actual booking details → cannot be a successful reservation
        print("FAILURE")
        return

    # Known Embarcadero restaurants inferred from training examples
    embarcadero_ids = set([
        'cd4f81d3-3c75-4c67-b47b-e7f013f6ae9d',  # River View Café
        '4be91a74-c7ff-4673-b60a-2c83d53a3052',  # Ocean Breeze
    ])
    embarcadero_names = set([
        normalize_name('River View Cafe'),
        normalize_name('River View Café'),
        normalize_name('Ocean Breeze'),
    ])

    success = False
    for item in details.values():
        if not isinstance(item, dict):
            continue
        rest = item.get('restaurant') or {}
        if not isinstance(rest, dict):
            continue
        rest_id = rest.get('id')
        rest_name = normalize_name(rest.get('name', ''))
        rating_raw = rest.get('rating')
        try:
            rating = float(rating_raw)
        except (TypeError, ValueError):
            rating = None
        # Date/time check to ensure a concrete reservation slot was selected
        date = item.get('date') or booking.get('date')
        time = item.get('time') or booking.get('time')

        is_embarcadero = (rest_id in embarcadero_ids) or (rest_name in embarcadero_names)
        has_slot = bool(date) and bool(time)
        over_three = (rating is not None) and (rating > 3.0)

        if is_embarcadero and has_slot and over_three:
            success = True
            break

    print("SUCCESS" if success else "FAILURE")

if __name__ == '__main__':
    main()
