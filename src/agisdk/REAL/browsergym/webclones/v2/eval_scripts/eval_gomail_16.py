# Verification script for: GoMail - Delete all emails from John Doe
# Strategy:
# - Success if the email from John Doe (id "1" in training data) was moved to Trash (emails.updated contains {id:1, trash:true}).
# - Additionally, ensure no John Doe email appears in the deleted list (which indicates a wrong action per failures).
# - Be robust to missing keys and types; default to FAILURE when uncertain.

import json
import sys

def norm_id(val):
    if val is None:
        return None
    try:
        return str(int(val))
    except Exception:
        return str(val)

try:
    path = sys.argv[1]
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    emails_diff = ((data or {}).get('differences') or {}).get('emails') or {}
    updated = emails_diff.get('updated') or []
    deleted = emails_diff.get('deleted') or []

    # Detect if any John Doe emails were permanently deleted (should not happen for success in training)
    is_john_in_deleted = False
    for e in deleted:
        from_field = (e or {}).get('from')
        if isinstance(from_field, str) and 'john.doe' in from_field.lower():
            is_john_in_deleted = True
            break

    # Detect if John's email (id 1 per dataset) was moved to trash
    john_id = '1'
    john_trashed = False
    for ch in updated:
        # Only accept explicit trash:true updates on the correct id
        if (isinstance(ch, dict) and ch.get('trash') is True and norm_id(ch.get('id')) == john_id):
            john_trashed = True
            break

    if john_trashed and not is_john_in_deleted:
        print("SUCCESS")
    else:
        print("FAILURE")
except Exception:
    # Any parsing/runtime issue -> conservative failure
    print("FAILURE")