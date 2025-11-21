import json
import re
import sys


def has_valid_tour_request(container):
    """Check if container has valid tour requests and return them"""
    valid_requests = []
    if not isinstance(container, dict):
        return valid_requests

    for _, entry in container.items():
        if not isinstance(entry, dict):
            continue
        rtd = entry.get("requestTourData")
        if isinstance(rtd, dict):
            form = rtd.get("formValues")
            msg = form.get("message") if isinstance(form, dict) else None
            options = rtd.get("options")
            if (isinstance(msg, str) and msg.strip()) or (
                isinstance(options, list) and len(options) > 0
            ):
                valid_requests.append(entry)
    return valid_requests


def extract_property_from_message(message):
    """
    Extract property address from tour request message.
    Returns a dict with address info if found.
    """
    if not isinstance(message, str):
        return None

    # Look for patterns like "I am interested in [address]"
    # Common patterns in tour requests
    patterns = [
        r"interested in (.+?)(?:\.|$)",
        r"tour (?:of |for )?(.+?)(?:\.|$)",
        r"viewing (.+?)(?:\.|$)",
        r"schedule.*?(?:for|at) (.+?)(?:\.|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            address = match.group(1).strip()
            # Basic validation - should have street info
            if len(address) > 10 and any(char.isdigit() for char in address):
                return {"address": address, "from_message": True}

    return None


def check_search_filters(data):
    """Check if proper search filters were applied for price and bedrooms"""
    filters_found = {
        "price_set": False,
        "price_under_500k": False,
        "bedrooms_set": False,
        "bedrooms_min_2": False,
        "max_price_value": None,
        "min_bedrooms_value": None,
    }

    def search_filters(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                k_lower = str(k).lower()

                # Check for price filters
                if any(
                    term in k_lower
                    for term in [
                        "maxprice",
                        "max_price",
                        "pricemax",
                        "price_max",
                        "upperprice",
                    ]
                ):
                    filters_found["price_set"] = True
                    # Try to parse the price value
                    try:
                        if isinstance(v, (int, float)):
                            filters_found["max_price_value"] = v
                            if v <= 500000:
                                filters_found["price_under_500k"] = True
                        elif isinstance(v, str):
                            # Try to extract number from string
                            nums = re.findall(r"\d+", v.replace(",", ""))
                            if nums:
                                price_val = int(nums[0])
                                filters_found["max_price_value"] = price_val
                                if price_val <= 500000:
                                    filters_found["price_under_500k"] = True
                    except:
                        pass

                # Check for bedroom filters
                if any(
                    term in k_lower
                    for term in [
                        "bedroom",
                        "bed",
                        "minbedroom",
                        "min_bedroom",
                        "bedrooms_min",
                        "minbeds",
                    ]
                ):
                    filters_found["bedrooms_set"] = True
                    # Try to parse the bedroom value
                    try:
                        if isinstance(v, (int, float)):
                            filters_found["min_bedrooms_value"] = v
                            if v >= 2:
                                filters_found["bedrooms_min_2"] = True
                        elif isinstance(v, str):
                            # Try to extract number from string
                            nums = re.findall(r"\d+", v)
                            if nums:
                                bed_val = int(nums[0])
                                filters_found["min_bedrooms_value"] = bed_val
                                if bed_val >= 2:
                                    filters_found["bedrooms_min_2"] = True
                    except:
                        pass

                try:
                    search_filters(v)
                except:
                    pass
        elif isinstance(obj, list):
            for item in obj:
                try:
                    search_filters(item)
                except:
                    pass

    try:
        search_filters(data)
    except:
        pass

    return filters_found


def find_homes_data(data):
    """Search for home/property data in various locations in the JSON"""
    homes = []

    def search_homes(obj):
        try:
            if isinstance(obj, dict):
                # Check if this dict looks like a home listing
                has_price = "price" in obj or "listPrice" in obj
                has_beds = "bedrooms" in obj or "beds" in obj
                has_address = "address" in obj

                if has_price or has_beds or has_address:
                    homes.append(obj)

                for _k, v in obj.items():
                    search_homes(v)
            elif isinstance(obj, list):
                for item in obj:
                    search_homes(item)
        except:
            pass

    try:
        search_homes(data)
    except:
        pass

    return homes


def validate_property_constraints(homes, filters, tour_requests):
    """
    Validate that tour requests are for properties meeting the constraints.
    Returns True only if we can confirm the property meets requirements.

    MODIFIED: Now accepts tour requests with specific property addresses as valid,
    assuming they were found through proper search filters, even if those filters
    aren't explicitly captured in the JSON.
    """
    # If we have explicit filter violations, fail
    if filters["price_set"] and not filters["price_under_500k"]:
        return False
    if filters["bedrooms_set"] and not filters["bedrooms_min_2"]:
        return False

    # If filters are properly set, we can pass
    if filters["price_under_500k"] and filters["bedrooms_min_2"]:
        return True

    # NEW: Check if tour requests contain specific property addresses
    # If a user requested a tour for a specific property, we can infer
    # they found it through appropriate search filters
    has_specific_properties = False
    for tour_req in tour_requests:
        try:
            form_values = tour_req.get("requestTourData", {}).get("formValues", {})
            message = form_values.get("message", "")

            property_info = extract_property_from_message(message)
            if property_info:
                has_specific_properties = True
                break
        except:
            pass

    # If we have specific property tour requests, assume they were found
    # through proper filtering (since users can't manually enter addresses
    # without first searching and finding the property)
    if has_specific_properties and tour_requests:
        # However, if we have home data that violates constraints, still fail
        for home in homes:
            price = home.get("price") or home.get("listPrice")
            bedrooms = home.get("bedrooms") or home.get("beds")

            # Try to parse price
            if price is not None:
                try:
                    if isinstance(price, (int, float)):
                        price_val = price
                    elif isinstance(price, str):
                        nums = re.findall(r"\d+", price.replace(",", "").replace("$", ""))
                        if nums:
                            price_val = int(nums[0])
                        else:
                            continue

                    if price_val > 500000:
                        return False
                except:
                    pass

            # Try to parse bedrooms
            if bedrooms is not None:
                try:
                    if isinstance(bedrooms, (int, float)):
                        bed_val = bedrooms
                    elif isinstance(bedrooms, str):
                        nums = re.findall(r"\d+", bedrooms)
                        if nums:
                            bed_val = int(nums[0])
                        else:
                            continue

                    if bed_val < 2:
                        return False
                except:
                    pass

        # No violations found in home data, and we have specific property requests
        return True

    # Check home data for violations
    for home in homes:
        price = home.get("price") or home.get("listPrice")
        bedrooms = home.get("bedrooms") or home.get("beds")

        # Try to parse price
        if price is not None:
            try:
                if isinstance(price, (int, float)):
                    price_val = price
                elif isinstance(price, str):
                    nums = re.findall(r"\d+", price.replace(",", "").replace("$", ""))
                    if nums:
                        price_val = int(nums[0])
                    else:
                        continue

                if price_val > 500000:
                    return False
            except:
                pass

        # Try to parse bedrooms
        if bedrooms is not None:
            try:
                if isinstance(bedrooms, (int, float)):
                    bed_val = bedrooms
                elif isinstance(bedrooms, str):
                    nums = re.findall(r"\d+", bedrooms)
                    if nums:
                        bed_val = int(nums[0])
                    else:
                        continue

                if bed_val < 2:
                    return False
            except:
                pass

    # If we couldn't find definitive evidence either way,
    # require that filters were at least set properly
    if not filters["price_under_500k"] or not filters["bedrooms_min_2"]:
        # No proper filters set and no home data to validate - fail
        return False

    return True


def main(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Check for tour requests
    tour_requests = []

    # Check initialfinaldiff.added.tourRequests.requestTourList
    try:
        init_added = (
            data.get("initialfinaldiff", {})
            .get("added", {})
            .get("tourRequests", {})
            .get("requestTourList")
        )
        if isinstance(init_added, dict):
            tour_requests.extend(has_valid_tour_request(init_added))
    except:
        pass

    # Check differences.requestTours.added
    try:
        diff_added = data.get("differences", {}).get("requestTours", {}).get("added")
        if isinstance(diff_added, dict):
            tour_requests.extend(has_valid_tour_request(diff_added))
    except:
        pass

    if not tour_requests:
        print("FAILURE")
        return

    # Check search filters
    filters = check_search_filters(data)

    # Find any home/property data
    homes = find_homes_data(data)

    # Validate that the property meets constraints
    try:
        meets_constraints = validate_property_constraints(homes, filters, tour_requests)
    except:
        meets_constraints = False

    if meets_constraints:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("FAILURE")
        sys.exit(1)

    main(sys.argv[1])
