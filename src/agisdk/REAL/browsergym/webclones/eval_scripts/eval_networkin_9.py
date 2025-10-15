import json, sys

# Strategy in code:
# 1) Confirm a user-authored invitation message was sent: look for any text message by 'divgarg' whose content contains 'new project' (case-insensitive),
#    from either messages list/dict or lastMessage fields in chatroomData found under both 'added' and 'updated'.
# 2) Confirm evidence of targeting either New York OR tech industry by scanning search terms/history and router query for NYC or tech keywords.
#    This prevents passing cases with only connections or with no NY/tech context.

def get_nested(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    return cur


def iter_chatrooms(diff_section):
    if not isinstance(diff_section, dict):
        return
    ui = diff_section.get('ui') or {}
    messaging = ui.get('messaging') or {}
    chatroom_data = messaging.get('chatroomData') or {}
    if isinstance(chatroom_data, dict):
        for room_id, room in chatroom_data.items():
            if isinstance(room, dict):
                yield room


def extract_messages_from_room(room):
    texts = []
    # messages may be a list or dict of messages
    msgs = room.get('messages')
    if isinstance(msgs, list):
        for m in msgs:
            if isinstance(m, dict):
                texts.append(m)
    elif isinstance(msgs, dict):
        for m in msgs.values():
            if isinstance(m, dict):
                texts.append(m)
    # lastMessage as a fallback snapshot
    last_msg = room.get('lastMessage')
    last_author = room.get('lastMessageAuthorId')
    if isinstance(last_msg, str) and last_author:
        texts.append({'message': last_msg, 'authorId': last_author, 'type': 'text'})
    return texts


def invitation_message_sent(data):
    # scan both added and updated sections
    invited = False
    for section_name in ['added', 'updated']:
        section = data.get('initialfinaldiff', {}).get(section_name) or {}
        for room in iter_chatrooms(section):
            for msg in extract_messages_from_room(room):
                if not isinstance(msg, dict):
                    continue
                author = (msg.get('authorId') or '').lower()
                mtype = (msg.get('type') or '').lower()
                text = (msg.get('message') or '')
                if not isinstance(text, str):
                    continue
                text_l = text.lower()
                # must be authored by the user and a text-type message (avoid system notices)
                if author == 'divgarg' and (mtype == 'text' or mtype == ''):
                    if 'new project' in text_l:
                        invited = True
                        break
            if invited:
                break
        if invited:
            break
    return invited


def collect_search_texts(data):
    vals = []
    for section_name in ['added', 'updated']:
        section = data.get('initialfinaldiff', {}).get(section_name) or {}
        # ui.searchTerm
        ui = section.get('ui') or {}
        st = ui.get('searchTerm')
        if isinstance(st, str):
            vals.append(st)
        # ui.searchHistory.*.searchTerm
        sh = ui.get('searchHistory') or {}
        if isinstance(sh, dict):
            for v in sh.values():
                if isinstance(v, dict):
                    term = v.get('searchTerm')
                    if isinstance(term, str):
                        vals.append(term)
        # router.location.search
        router = section.get('router') or {}
        location = router.get('location') or {}
        q = location.get('search')
        if isinstance(q, str):
            vals.append(q)
    return vals


def has_context_evidence(data):
    texts = collect_search_texts(data)
    blob = ' '.join([t for t in texts if isinstance(t, str)]).lower()
    nyc_terms = [
        'new york', 'new+york', 'new%20york', 'new york city', 'nyc', 'brooklyn',
        'manhattan', 'queens', 'bronx', 'staten island', 'ny'
    ]
    tech_terms = [
        'engineer', 'developer', 'software', 'frontend', 'back-end', 'backend', 'full stack', 'full-stack',
        'devops', 'qa', 'quality assurance', 'data', 'scientist', 'analyst', 'designer', 'product', 'ux', 'ui',
        'it', 'cloud', 'systems', 'cybersecurity', 'security', 'architect', 'programmer', 'technology', 'tech'
    ]
    ny_hit = any(term in blob for term in nyc_terms)
    tech_hit = any(term in blob for term in tech_terms)
    return ny_hit or tech_hit


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    invited = invitation_message_sent(data)
    context_ok = has_context_evidence(data)

    if invited and context_ok:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
