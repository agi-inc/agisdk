import json
import sys

# Strategy in code:
# - Load final_state_diff.json and inspect differences.emails.updated for emails moved to Trash (trash == true).
# - If no emails moved to Trash -> FAILURE.
# - If a snackbar message like "X conversations moved to Trash" exists, use X: small counts imply partial action -> FAILURE; larger counts -> SUCCESS.
# - If no snackbar, use a conservative threshold (>=10 moved to Trash) to infer clearing of a visible batch -> SUCCESS; else -> FAILURE.
# - Also handle clear failures where only isRead/selected flags changed without trashing.


def get_nested(data, keys, default=None):
    cur = data
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def extract_first_int(s):
    num = ''
    for ch in s:
        if ch.isdigit():
            num += ch
            # continue to capture multi-digit number
        elif num:
            break
    return int(num) if num else None


def find_snackbar_count(obj):
    # Search recursively for a snackbar message containing the phrase
    target_phrase = 'conversations moved to Trash'
    def recurse(o):
        if isinstance(o, dict):
            # Direct path check
            if 'snackbar' in o and isinstance(o['snackbar'], dict):
                msg = o['snackbar'].get('message')
                if isinstance(msg, str) and target_phrase in msg:
                    return msg
            # Generic message search
            for v in o.values():
                res = recurse(v)
                if res:
                    return res
        elif isinstance(o, list):
            for v in o:
                res = recurse(v)
                if res:
                    return res
        return None

    msg = recurse(obj)
    if isinstance(msg, str) and target_phrase in msg:
        n = extract_first_int(msg)
        return n
    return None


def main():
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    diffs = get_nested(data, ['differences'], {})
    emails = diffs.get('emails') or {}
    updated = emails.get('updated') or []

    # Count emails moved to trash
    moved_ids = set()
    any_trash_update = False
    only_read_or_selected = True  # assume until we see a trash update

    for u in updated:
        if not isinstance(u, dict):
            continue
        if u.get('trash') is True:
            any_trash_update = True
            only_read_or_selected = False
            # Record id if present
            uid = str(u.get('id')) if u.get('id') is not None else None
            if uid is not None:
                moved_ids.add(uid)
        else:
            # If any update is not just read/selected, keep only_read_or_selected as is
            # But we specifically want to detect cases where only isRead/selected toggled and no trash happened
            pass

    # Detect explicit failure patterns: only read/selected changes without any trash
    if not any_trash_update:
        print('FAILURE')
        return

    # Try to use snackbar message count if available
    snackbar_count = find_snackbar_count(data)

    if isinstance(snackbar_count, int):
        # If snackbar indicates only a tiny number moved, it's likely not a full visible clear
        if snackbar_count >= 10:
            print('SUCCESS')
        else:
            print('FAILURE')
        return

    # No snackbar guidance; fallback on threshold of moved-to-trash items
    # Use a conservative minimum to infer a visible batch was cleared
    num_moved = len(moved_ids) if moved_ids else 0

    if num_moved >= 10:
        print('SUCCESS')
    else:
        print('FAILURE')


if __name__ == '__main__':
    main()
