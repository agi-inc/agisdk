import json, sys

# Strategy:
# Determine success if the final state indicates a contact agent action occurred.
# Specifically, look for at least one entry in either initialfinaldiff.added.tourRequests.contactAgentList
# or differences.contactAgents.added that contains contactAgentData.formValues with non-empty identifying fields.

def safe_get(d, path, default=None):
    cur = d
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def extract_form_values(container):
    """
    Given a dict container that maps arbitrary keys to entries, each possibly containing
    contactAgentData.formValues, yield the formValues dicts found.
    """
    if not isinstance(container, dict):
        return
    for _k, v in container.items():
        if isinstance(v, dict):
            # Typical path
            fv = safe_get(v, ["contactAgentData", "formValues"], None)
            if isinstance(fv, dict):
                yield fv
            else:
                # In case formValues sits at root of v (defensive)
                if isinstance(v.get("formValues"), dict):
                    yield v.get("formValues")


def has_valid_contact_submission(data):
    # Paths to check
    contact_list = safe_get(data, ["initialfinaldiff", "added", "tourRequests", "contactAgentList"], {})
    contact_added = safe_get(data, ["differences", "contactAgents", "added"], {})

    def fv_has_identity(fv):
        if not isinstance(fv, dict):
            return False
        # Consider valid if at least one of email/phone/name is a non-empty string
        for field in ("email", "phone", "name"):
            val = fv.get(field)
            if isinstance(val, str) and val.strip() != "":
                return True
        return False

    # Check both containers for at least one valid formValues
    for container in (contact_list, contact_added):
        if isinstance(container, dict) and container:
            for fv in extract_form_values(container):
                if fv_has_identity(fv):
                    return True
    return False


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    if has_valid_contact_submission(data):
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()