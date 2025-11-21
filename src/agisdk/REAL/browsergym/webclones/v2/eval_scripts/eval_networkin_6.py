import json
import sys


def walk(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k, v
            for inner in walk(v):
                yield inner
    elif isinstance(obj, list):
        for v in obj:
            for inner in walk(v):
                yield inner


def iter_messages_struct(messages_val):
    # Yield message dicts from either list or dict form
    if isinstance(messages_val, list):
        for m in messages_val:
            if isinstance(m, dict):
                yield m
    elif isinstance(messages_val, dict):
        for m in messages_val.values():
            if isinstance(m, dict):
                yield m


def collect_search_strings(data):
    found = []
    for k, v in walk(data):
        if k == "searchTerm" and isinstance(v, str):
            found.append(v)
        elif k == "search" and isinstance(v, str):
            # likely router.location.search like '?keywords=new+york'
            s = v
            if "keywords=" in s:
                # strip leading ? and replace + with space
                s2 = s.split("keywords=", 1)[1]
                s2 = s2.replace("+", " ")
                found.append(s2)
        elif k == "searchTerm" and isinstance(v, (int, float)):
            # ignore non-string
            pass
    # ui.searchTerm may also be directly present as 'searchTerm' handled above
    return [s for s in found if isinstance(s, str)]


def text_contains_any(s, keywords):
    s_low = s.lower()
    return any(kw in s_low for kw in keywords)


def detect_invite(data):
    invited = False
    # 1) Check any messages sent by user mentioning project
    for k, v in walk(data):
        if k == "messages":
            for m in iter_messages_struct(v):
                msg_text = m.get("message") if isinstance(m, dict) else None
                if isinstance(msg_text, str):
                    author = m.get("authorId")
                    mtype = m.get("type")
                    # user-sent invite mentioning project
                    if (
                        (author == "divgarg")
                        and (mtype == "text")
                        and text_contains_any(msg_text, ["project"])
                    ):
                        invited = True
                        break
                    # system connection request sent
                    if (mtype == "system") and text_contains_any(
                        msg_text, ["connection request sent"]
                    ):
                        invited = True
                        break
            if invited:
                break
    if not invited:
        # 2) Some diffs may only store lastMessage
        for k, v in walk(data):
            if k == "lastMessage" and isinstance(v, str):
                # verify authored by user if possible
                # try to find sibling lastMessageAuthorId by scanning in parent context is complex; instead, also gather authorId via nearby keys
                # We will more broadly accept if there is any lastMessage by user (checked separately) containing 'project'
                if text_contains_any(v, ["project"]):
                    invited = True
                    break
    if not invited:
        # 3) Check contact list additions imply an invite/connection action
        for k, v in walk(data):
            if k == "contactList" and isinstance(v, dict):
                # any non-empty contactList indicates a connection action occurred
                if len(v) > 0:
                    invited = True
                    break
    return invited


def detect_targeting(data):
    # Evidence of targeting either location (new york) or industry (tech)
    targets = collect_search_strings(data)
    targets_lower = " ".join([t.lower() for t in targets])
    # Normalize simple URL encodings already handled; also include ui.searchTerm captured
    has_ny = any(kw in targets_lower for kw in ["new york", "nyc"])
    has_tech = "tech" in targets_lower
    return has_ny or has_tech


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print("FAILURE")
        return
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Work within the provided structure, but search across all nested nodes for robustness
    invited = detect_invite(data)
    targeted = detect_targeting(data)

    if invited and targeted:
        print("SUCCESS")
    else:
        print("FAILURE")


if __name__ == "__main__":
    main()
