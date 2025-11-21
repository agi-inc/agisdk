import json
import sys


def iter_dicts_with_key(obj, target_key):
    """Yield values of any dict entries where key == target_key, recursively through dicts/lists."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == target_key:
                yield v
            # Recurse into values
            for found in iter_dicts_with_key(v, target_key):
                yield found
    elif isinstance(obj, list):
        for item in obj:
            for found in iter_dicts_with_key(item, target_key):
                yield found


def has_olivia_in_contact_list(data):
    # Check any 'contactList' dicts for values equal to 'oliviamartinez'
    for cl in iter_dicts_with_key(data, "contactList"):
        if isinstance(cl, dict):
            for v in cl.values():
                if isinstance(v, str) and v.lower() == "oliviamartinez":
                    return True
    return False


def has_olivia_chatroom(data):
    # Check any 'chatroomData' dicts for a key 'oliviamartinez'
    for cr in iter_dicts_with_key(data, "chatroomData"):
        if isinstance(cr, dict):
            # direct key presence indicates a chat entry for Olivia
            for key in cr.keys():
                if isinstance(key, str) and key.lower() == "oliviamartinez":
                    return True
    return False


def has_olivia_connection_grade(data):
    # Check any 'connectionGrades' dicts for key 'oliviamartinez'
    for cg in iter_dicts_with_key(data, "connectionGrades"):
        if isinstance(cg, dict):
            for key in cg.keys():
                if isinstance(key, str) and key.lower() == "oliviamartinez":
                    return True
    return False


def main():
    try:
        path = sys.argv[1]
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Strategy: Success if evidence shows Olivia Martinez connection established.
    # Evidence includes: contactList containing 'oliviamartinez', chatroomData with key 'oliviamartinez', or connectionGrades listing 'oliviamartinez'.
    # Search recursively across the diff structure to be robust to nesting variations.

    success = (
        has_olivia_in_contact_list(data)
        or has_olivia_chatroom(data)
        or has_olivia_connection_grade(data)
    )

    print("SUCCESS" if success else "FAILURE")


if __name__ == "__main__":
    main()
