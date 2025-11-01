import sys, json

def get_nested(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

def parse_first_int(s):
    if not isinstance(s, str):
        return None
    num = ''
    found = False
    for ch in s:
        if ch.isdigit():
            num += ch
            found = True
        else:
            if found:
                break
    if num:
        try:
            return int(num)
        except Exception:
            return None
    return None

def main():
    import sys, json
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

    # Extract differences
    emails_diff = get_nested(data, ["differences", "emails"], {}) or {}
    updated_list = emails_diff.get("updated", []) or []
    deleted_list = emails_diff.get("deleted", []) or []

    # Count updates setting trash to True/False in differences
    updated_trash_true = 0
    updated_trash_false = 0
    for item in updated_list:
        # item is expected to be a dict, may include 'trash'
        if isinstance(item, dict):
            if "trash" in item:
                if bool(item.get("trash")) is True:
                    updated_trash_true += 1
                else:
                    updated_trash_false += 1

    # Extract additional updates from initialfinaldiff (earlier changes in the session)
    if isinstance(data.get("initialfinaldiff"), dict):
        email_updates_map = get_nested(data, ["initialfinaldiff", "updated", "email", "emails"], {}) or {}
        init_trash_true = 0
        init_trash_false = 0
        if isinstance(email_updates_map, dict):
            for k, v in email_updates_map.items():
                if isinstance(v, dict) and "trash" in v:
                    if bool(v.get("trash")) is True:
                        init_trash_true += 1
                    else:
                        init_trash_false += 1
    else:
        init_trash_true = 0
        init_trash_false = 0

    # Look for UI snackbar confirmation like "54 conversations moved to Trash"
    snackbar_msg = get_nested(data, ["initialfinaldiff", "updated", "ui", "snackbar", "message"], None)
    moved_count_from_ui = None
    if snackbar_msg and isinstance(snackbar_msg, str) and ("moved to Trash" in snackbar_msg or "moved to trash" in snackbar_msg.lower()):
        moved_count_from_ui = parse_first_int(snackbar_msg)

    # Decision logic:
    # - Any deletions indicate the inbox wasn’t emptied by moving to Trash -> FAILURE
    # - Otherwise, we require strong evidence that the bulk of emails were trashed:
    #   Use UI count if available, else require a high count threshold (>=50) based on typical inbox size in this task.

    deleted_count = len(deleted_list)
    total_trash_true = updated_trash_true + init_trash_true

    # If any item was explicitly updated with trash False, it's a red flag
    if updated_trash_false > 0 or init_trash_false > 0:
        print("FAILURE")
        return

    if deleted_count > 0:
        # Items were removed rather than moved to Trash
        print("FAILURE")
        return

    # Use UI message if present
    if moved_count_from_ui is not None and moved_count_from_ui > 0:
        if total_trash_true >= moved_count_from_ui:
            print("SUCCESS")
            return
        else:
            print("FAILURE")
            return

    # Fallback: require a large number of emails moved to trash and no deletions
    # Based on training data, successful runs move ~54 conversations.
    if total_trash_true >= 50:
        print("SUCCESS")
        return

    # If we reach here, evidence is insufficient
    print("FAILURE")

if __name__ == "__main__":
    main()