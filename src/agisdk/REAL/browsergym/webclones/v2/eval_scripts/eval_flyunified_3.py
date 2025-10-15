import json, sys

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

# Helper to safely get booking object from either added or updated sections
def get_booking(data):
    idiff = data.get('initialfinaldiff', {})
    for section in ('added', 'updated'):
        sec = idiff.get(section, {})
        if isinstance(sec, dict) and isinstance(sec.get('booking'), dict):
            return sec.get('booking')
    # Fallback: sometimes booking might be directly under root (unlikely but safe)
    return data.get('booking', {}) if isinstance(data.get('booking'), dict) else {}

# Extract airport code from a leg endpoint object
def get_airport_code(endpoint):
    if not isinstance(endpoint, dict):
        return None
    # Prefer nested destination dict
    dest = endpoint.get('destination')
    if isinstance(dest, dict):
        code = dest.get('code') or dest.get('airportCode') or dest.get('iata')
        if code:
            return str(code).upper()
    # Fallback to direct code field
    code = endpoint.get('code') or endpoint.get('airportCode') or endpoint.get('iata')
    return str(code).upper() if code else None

# Extract departure month (1-12) from ISO-like datetime string
def get_month_from_date_str(s):
    if not isinstance(s, str) or len(s) < 7:
        return None
    # Expect format YYYY-MM-...; be defensive
    try:
        # Find first '-' and second '-'
        parts = s.split('T')[0].split('-')
        if len(parts) >= 2:
            return int(parts[1])
    except Exception:
        return None
    return None

# Determine if the task succeeded
# Criteria:
# - There are two selected flights: outbound LAX -> Chicago in August, return Chicago -> LAX in October
# - We verify using booking.selectedFlights entries; do not rely solely on form fields to avoid false positives

def evaluate_success(data):
    booking = get_booking(data)
    selected = booking.get('selectedFlights')
    if not isinstance(selected, dict) or not selected:
        return False

    chicago_codes = {"ORD", "MDW"}
    lax = "LAX"

    found_outbound = False  # LAX -> CHI in August
    found_return = False    # CHI -> LAX in October

    for key, flight in selected.items():
        if not isinstance(flight, dict):
            continue
        frm = flight.get('from')
        to = flight.get('to')
        from_code = get_airport_code(frm)
        to_code = get_airport_code(to)
        # Departure date is typically stored in from.date
        dep_date = frm.get('date') if isinstance(frm, dict) else None
        dep_month = get_month_from_date_str(dep_date) if dep_date else None

        if from_code == lax and to_code in chicago_codes and dep_month == 8:
            found_outbound = True
        if from_code in chicago_codes and to_code == lax and dep_month == 10:
            found_return = True

    return found_outbound and found_return


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        data = load_json(path)
    except Exception:
        print("FAILURE")
        return

    result = evaluate_success(data)
    print("SUCCESS" if result else "FAILURE")

if __name__ == "__main__":
    # Strategy: Confirm two selected flights with correct directions and months (Aug outbound, Oct return) using detailed selectedFlights info.
    # This avoids relying on mere form inputs; requires actual flights found/selected matching the task goal.
    main()
