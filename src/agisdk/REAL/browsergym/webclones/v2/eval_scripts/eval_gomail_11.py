# Verification script for the task:
# "Turn on all labels in my email settings, then clear all emails with alerts. Lastly tell John Doe thank you for the meeting notes."
#
# Strategy:
# 1) Consider "clear all emails with alerts" as ensuring specific known alert emails (IDs 3,7,14,28,48)
#    are moved to trash (trash:true) and not incorrectly marked as spam.
# 2) Verify a proper reply was sent to john.doe@example.com with a message containing "thank" (case-insensitive),
#    using the reply mechanism (isReply:true or subject starting with "Re:").
#
# If both conditions are satisfied -> print SUCCESS, else FAILURE.

import sys, json

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_nested(d, *keys):
    cur = d
    for k in keys:
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return None
    return cur


def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    data = load_json(sys.argv[1])
    diffs = get_nested(data, 'differences') or {}
    emails = diffs.get('emails', {}) if isinstance(diffs, dict) else {}

    added = emails.get('added') or []
    updated = emails.get('updated') or []

    # 1) Check reply sent to John Doe with thank-you content
    reply_ok = False
    for e in added:
        if not isinstance(e, dict):
            continue
        sent = e.get('sent') is True
        to_list = e.get('to') or []
        # Normalize recipients to lower-case strings
        to_list_norm = [str(x).lower() for x in to_list]
        to_john = any('john.doe@example.com' == t for t in to_list_norm)
        content = (e.get('content') or '')
        content_str = content if isinstance(content, str) else str(content)
        has_thanks = 'thank' in content_str.lower()
        subj = (e.get('subject') or '')
        subj_str = subj if isinstance(subj, str) else str(subj)
        is_reply_flag = e.get('isReply') is True or subj_str.strip().lower().startswith('re:')
        if sent and to_john and has_thanks and is_reply_flag:
            reply_ok = True
            break

    # 2) Check clearing alert emails: IDs 3,7,14,28,48 must be trashed and not spammed
    alert_ids = {"3", "7", "14", "28", "48"}
    updated_map = {}
    for u in updated:
        if not isinstance(u, dict):
            continue
        uid = str(u.get('id')) if u.get('id') is not None else None
        if uid is None:
            continue
        updated_map[uid] = u if uid not in updated_map else {**updated_map[uid], **u}

    cleared_ok = True
    for aid in alert_ids:
        u = updated_map.get(aid)
        # Must exist and have trash:true
        if not u or u.get('trash') is not True:
            cleared_ok = False
            break
        # Should not be marked as spam when clearing alerts
        if u.get('spam') is True:
            cleared_ok = False
            break

    if reply_ok and cleared_ok:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
