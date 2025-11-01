import sys, json

def extract_first_int(s):
    num = ''
    found = False
    for ch in s:
        if ch.isdigit():
            num += ch
            found = True
        elif found:
            break
    if num:
        try:
            return int(num)
        except:
            return None
    return None

def main():
    import sys
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

    # Extract updated email changes
    differences = data.get('differences', {})
    emails = differences.get('emails', {})
    updated_list = emails.get('updated', [])

    # Count emails that were moved to trash in the differences
    trash_updates = [u for u in updated_list if isinstance(u, dict) and u.get('trash') is True]
    trash_count = len(trash_updates)

    # Extract snackbar message (number of conversations moved)
    msg = None
    initdiff = data.get('initialfinaldiff', {})
    if isinstance(initdiff, dict):
        upd = initdiff.get('updated', {}) if isinstance(initdiff.get('updated', {}), dict) else {}
        ui = upd.get('ui', {}) if isinstance(upd.get('ui', {}), dict) else {}
        sb = ui.get('snackbar', {}) if isinstance(ui.get('snackbar', {}), dict) else {}
        msg = sb.get('message') if isinstance(sb.get('message'), str) else None
    if msg is None:
        # Fallback in case snackbar is placed elsewhere (unlikely but safer)
        ui2 = differences.get('ui', {}) if isinstance(differences.get('ui', {}), dict) else {}
        sb2 = ui2.get('snackbar', {}) if isinstance(ui2.get('snackbar', {}), dict) else {}
        msg = sb2.get('message') if isinstance(sb2.get('message'), str) else None

    moved_count = None
    if isinstance(msg, str) and 'moved to Trash' in msg:
        moved_count = extract_first_int(msg)

    # Decision logic:
    # - Must have actually trashed at least one email
    if trash_count <= 0:
        print("FAILURE")
        return

    # If we have a snackbar count, use it to validate scope
    if moved_count is not None:
        # If they cleared essentially all emails (way beyond a visible page), fail
        # Using threshold > 50 based on typical visible page size in training data
        if moved_count >= 51:
            print("FAILURE")
            return
        # If the number of trashed items in diffs is far larger than the last action count,
        # it suggests multiple deletion batches instead of a single visible clear.
        # Allow small discrepancy (e.g., starred toggles) but not huge gaps.
        if trash_count > moved_count + 5:
            print("FAILURE")
            return
        # Otherwise, looks like a single visible-page clear
        print("SUCCESS")
        return

    # Without snackbar info, accept as success if some emails were trashed
    print("SUCCESS")

if __name__ == '__main__':
    main()
