import json
import re
import sys
from datetime import datetime, timedelta


def extract_contact_entries(data):
    entries = []
    # From differences.contactAgents.added
    try:
        added = data.get("differences", {}).get("contactAgents", {}).get("added", {})
        if isinstance(added, dict):
            for _, v in added.items():
                if isinstance(v, dict):
                    entries.append(v)
    except Exception:
        pass
    # From initialfinaldiff.added.tourRequests.contactAgentList
    try:
        clist = (
            data.get("initialfinaldiff", {})
            .get("added", {})
            .get("tourRequests", {})
            .get("contactAgentList", {})
        )
        if isinstance(clist, dict):
            for _, v in clist.items():
                if isinstance(v, dict):
                    entries.append(v)
    except Exception:
        pass
    return entries


def get_current_date_from_data(data):
    """
    Try to extract the current/test date from the data.
    Look for timestamp fields or creation dates.
    """
    try:
        # Check for createdAt or timestamp fields in the data
        def find_dates(obj, dates_list):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    k_lower = str(k).lower()
                    if k_lower in ["createdat", "timestamp", "date", "currentdate"]:
                        if isinstance(v, str) and "T" in v:
                            dates_list.append(v)
                    find_dates(v, dates_list)
            elif isinstance(obj, list):
                for item in obj:
                    find_dates(item, dates_list)

        dates = []
        find_dates(data, dates)

        if dates:
            # Parse the first date found and use it as reference
            first_date = dates[0][:10]  # Get YYYY-MM-DD
            return first_date
    except Exception:
        pass

    return None


def check_search_filters(data):
    """Check if proper search filters were applied for Boston and price < 1M"""
    filters_found = {
        "location": False,
        "price": False,
        "boston_mentioned": False,
        "price_under_1m": False,
    }

    def search_filters(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = str(k).lower()

                # Check for location filters
                if any(
                    term in k_lower
                    for term in [
                        "location",
                        "city",
                        "place",
                        "region",
                        "area",
                        "search",
                        "query",
                    ]
                ):
                    if isinstance(v, str):
                        v_lower = v.lower()
                        if "boston" in v_lower or "boston, ma" in v_lower:
                            filters_found["boston_mentioned"] = True
                            filters_found["location"] = True

                # Check for price filters
                if any(
                    term in k_lower
                    for term in [
                        "price",
                        "maxprice",
                        "max_price",
                        "pricemax",
                        "pricerange",
                    ]
                ):
                    filters_found["price"] = True
                    # Try to parse the price value
                    if isinstance(v, (int, float)):
                        if v <= 1000000:
                            filters_found["price_under_1m"] = True
                    elif isinstance(v, str):
                        # Try to extract number from string
                        nums = re.findall(r"\d+", v.replace(",", ""))
                        if nums:
                            price_val = int(nums[0])
                            if price_val <= 1000000:
                                filters_found["price_under_1m"] = True

                search_filters(v)
        elif isinstance(obj, list):
            for item in obj:
                search_filters(item)

    search_filters(data)
    return filters_found


def extract_location_from_message(message):
    """Extract city and state from the message"""
    if not isinstance(message, str):
        return None, None

    # Common pattern: "City, STATE" or "Address, City, STATE ZIP"
    message.lower()

    # Look for state abbreviations
    state_pattern = r",\s*([A-Z]{2})\s*\d{5}"
    state_match = re.search(state_pattern, message)
    if state_match:
        state = state_match.group(1)

        # Try to find city before the state
        city_pattern = r",\s*([^,]+),\s*" + state
        city_match = re.search(city_pattern, message)
        if city_match:
            city = city_match.group(1).strip()
            return city.lower(), state.upper()

    return None, None


def to_date_str(date_str):
    if not date_str or not isinstance(date_str, str):
        return None
    # Expect ISO-like 'YYYY-MM-DDTHH:MM:SSZ'
    try:
        return date_str[:10]
    except Exception:
        return None


def main():
    path = sys.argv[1]
    with open(path) as f:
        data = json.load(f)

    entries = extract_contact_entries(data)
    if not entries:
        print("FAILURE")
        return

    # Try to get current date from data, otherwise use system date
    current_date_str = get_current_date_from_data(data)

    if current_date_str:
        try:
            current_date = datetime.strptime(current_date_str, "%Y-%m-%d")
        except Exception:
            current_date = datetime.now()
    else:
        current_date = datetime.now()

    # Calculate tomorrow's date
    tomorrow = current_date + timedelta(days=1)
    TARGET_TOMORROW = tomorrow.strftime("%Y-%m-%d")

    TARGET_CITY = "boston"
    TARGET_STATE = "MA"

    # Check if filters were properly set
    filters = check_search_filters(data)

    success_found = False

    for entry in entries:
        cad = entry.get("contactAgentData", {})
        form = cad.get("formValues", {}) if isinstance(cad, dict) else {}
        msg = form.get("message", "")
        if not isinstance(msg, str):
            msg = ""

        # Extract location from message
        city, state = extract_location_from_message(msg)

        # Check if location is correct (Boston, MA)
        location_correct = False
        if city and state:
            location_correct = TARGET_CITY in city.lower() and state == TARGET_STATE

        # Fail if wrong location
        if city and state and not location_correct:
            # Wrong location mentioned
            continue

        # Fail if explicitly mentions wrong locations
        msg_lower = msg.lower()
        wrong_locations = [
            "san francisco",
            "los angeles",
            "escondido",
            "san diego",
            "sacramento",
        ]
        if any(loc in msg_lower for loc in wrong_locations):
            continue

        # Check date
        sel = cad.get("selectedDate", {}) if isinstance(cad, dict) else {}
        date_str = to_date_str(sel.get("date"))

        if date_str == TARGET_TOMORROW:
            # Date is correct, but we also need correct location
            if location_correct or filters["boston_mentioned"]:
                success_found = True
                break

    # Additional validation: if filters weren't set for Boston, fail
    if success_found and not filters["boston_mentioned"]:
        # Check if the contacted home's location suggests Boston
        # If we can't confirm Boston, fail
        success_found = False

    print("SUCCESS" if success_found else "FAILURE")


if __name__ == "__main__":
    main()
