import json, sys

def get_in(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

# Strategy inside code:
# - Aggregate all updates from two places: differences.emails.updated (list) and initialfinaldiff.updated.email.emails (map)
# - Condition A (Amazon deletion): require IDs {"4","7","23","46"} to have trash==True OR UI indicates searching 'amazon' and snackbar mentions '4' and 'moved to Trash'
# - Condition B (Mark all as read): ensure no isRead==False updates anywhere AND at least one isRead==True update occurs (interpreting that unread ones were marked read)
# - Print SUCCESS only if both conditions satisfied; else FAILURE

def main():
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    # Collect updates from differences.emails.updated
    trashed_ids = set()
    has_isread_true = False
    has_isread_false = False

    diffs_updated = get_in(data, ["differences", "emails", "updated"], []) or []
    if isinstance(diffs_updated, list):
        for upd in diffs_updated:
            if not isinstance(upd, dict):
                continue
            eid = str(upd.get("id")) if upd.get("id") is not None else None
            if eid is not None:
                if upd.get("trash") is True:
                    trashed_ids.add(eid)
            if "isRead" in upd:
                val = upd.get("isRead")
                if val is True:
                    has_isread_true = True
                if val is False:
                    has_isread_false = True

    # Collect updates from initialfinaldiff.updated.email.emails (map of id -> fields)
    init_email_updates = get_in(data, ["initialfinaldiff", "updated", "email", "emails"], {}) or {}
    if isinstance(init_email_updates, dict):
        for eid, fields in init_email_updates.items():
            eid_str = str(eid)
            if isinstance(fields, dict):
                if fields.get("trash") is True:
                    trashed_ids.add(eid_str)
                if "isRead" in fields:
                    val = fields.get("isRead")
                    if val is True:
                        has_isread_true = True
                    if val is False:
                        has_isread_false = True

    # UI indicators (from initialfinaldiff or differences)
    # Prefer initialfinaldiff.updated.ui.snackbar.message and ui.searchInputValue
    ui_snackbar_msg = get_in(data, ["initialfinaldiff", "updated", "ui", "snackbar", "message"], "") or ""
    ui_search_value = get_in(data, ["initialfinaldiff", "updated", "ui", "searchInputValue"], "") or ""

    # Also try differences route in case some states place UI under differences
    if not ui_snackbar_msg:
        ui_snackbar_msg = get_in(data, ["differences", "ui", "snackbar", "message"], "") or ""
    if not ui_search_value:
        ui_search_value = get_in(data, ["differences", "ui", "searchInputValue"], "") or ""

    # Condition A: Amazon-related emails deleted
    amazon_ids = {"4", "7", "23", "46"}
    amazon_deleted_by_ids = amazon_ids.issubset(trashed_ids)

    # Alternative evidence: UI shows we searched amazon and moved 4 conversations to Trash
    msg_lower = ui_snackbar_msg.lower()
    search_lower = str(ui_search_value).lower()
    ui_indicates_amazon_deleted = ("amazon" in search_lower) and ("moved to trash" in msg_lower) and ("4" in ui_snackbar_msg)

    condition_amazon_deleted = amazon_deleted_by_ids or ui_indicates_amazon_deleted

    # Condition B: all emails marked as read (proxy via updates):
    # - No isRead false updates
    # - At least one isRead true update observed (indicates the action was performed)
    condition_marked_read = (not has_isread_false) and has_isread_true

    if condition_amazon_deleted and condition_marked_read:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == "__main__":
    main()
