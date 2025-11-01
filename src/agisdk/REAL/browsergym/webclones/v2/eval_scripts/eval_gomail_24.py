import json, sys

# Strategy:
# - Identify John Doe's email by id "1" (consistent in this GoMail dataset).
# - Success if differences.emails.updated contains an entry with id == "1" and trash == True.
# - UI snackbar text mentioning "moved to Trash" is supportive but not required to avoid overfitting.
# - Be robust to missing keys and id being int/str.

def get(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur

try:
    path = sys.argv[1]
    with open(path, 'r') as f:
        data = json.load(f)

    emails_diff = get(data, ['differences', 'emails'], {}) or {}
    updated_list = emails_diff.get('updated', []) or []

    john_id = '1'
    john_trashed = False

    for item in updated_list:
        # item may have id as int or str
        iid = str(item.get('id')) if item is not None else None
        trash_val = item.get('trash') if isinstance(item, dict) else None
        if iid == john_id and trash_val is True:
            john_trashed = True
            break

    # Optionally check UI snackbar (supportive only)
    snackbar_msg = get(data, ['initialfinaldiff', 'updated', 'ui', 'snackbar', 'message'], '') or ''
    moved_to_trash = isinstance(snackbar_msg, str) and ('moved to Trash' in snackbar_msg)

    if john_trashed:
        print('SUCCESS')
    else:
        print('FAILURE')
except Exception:
    # On any error, mark as failure
    print('FAILURE')