import json, sys

def main():
    # Strategy:
    # - Load final_state_diff.json and scan differences.emails.added for any email marked sent=true
    # - Validate it's addressed to Charles (any recipient containing 'charles' case-insensitive)
    # - Ensure the email content references 'new' and 'client' (asks about new clients)
    # - If any such email exists, print SUCCESS; otherwise, print FAILURE
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    diffs = (data or {}).get('differences', {})
    emails = diffs.get('emails', {})
    added = emails.get('added') or []

    def to_contains_charles(to_list):
        if not isinstance(to_list, list):
            return False
        for addr in to_list:
            try:
                if isinstance(addr, str) and 'charles' in addr.lower():
                    return True
            except Exception:
                continue
        return False

    success = False
    for em in added:
        if not isinstance(em, dict):
            continue
        if not em.get('sent', False):
            continue
        if not to_contains_charles(em.get('to')):
            continue
        content = em.get('content') or ''
        if not isinstance(content, str):
            content = str(content)
        content_l = content.lower()
        # Require reference to clients and the notion of new
        if ('client' in content_l) and ('new' in content_l):
            success = True
            break

    print("SUCCESS" if success else "FAILURE")

if __name__ == '__main__':
    main()
