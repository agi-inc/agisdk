import json, sys

def main():
    # Strategy:
    # 1) Confirm a reply to Jane Smith was sent by checking an added email with sent=True, isReply=True,
    #    addressed to jane.smith@example.com, and linked to Jane's thread (originalEmailId "2" or threadId "thread_2").
    # 2) Confirm deletion precisely of all and only the support emails by ensuring the set of trashed IDs equals
    #    the known set {3,7,11,21,25,29,35,37,43,46,49,51,53}.

    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    emails = (data.get('differences') or {}).get('emails') or {}
    added = emails.get('added') or []
    updated = emails.get('updated') or []

    # Check reply to Jane
    replied = False
    for e in added:
        try:
            sent = bool(e.get('sent'))
            is_reply = bool(e.get('isReply'))
            to_list = e.get('to') or []
            to_list = to_list if isinstance(to_list, list) else [to_list]
            to_match = any(isinstance(x, str) and x.strip().lower() == 'jane.smith@example.com' for x in to_list)
            thread_match = (e.get('originalEmailId') == '2') or (e.get('threadId') == 'thread_2')
            if sent and is_reply and to_match and thread_match:
                replied = True
                break
        except Exception:
            continue

    # Check deletion of support emails exactly
    support_ids = {"3","7","11","21","25","29","35","37","43","46","49","51","53"}
    trashed_ids = set()
    for u in updated:
        try:
            if u.get('trash') is True:
                uid = str(u.get('id')) if u.get('id') is not None else None
                if uid:
                    trashed_ids.add(uid)
        except Exception:
            continue

    correct_deletions = (trashed_ids == support_ids)

    if replied and correct_deletions:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()