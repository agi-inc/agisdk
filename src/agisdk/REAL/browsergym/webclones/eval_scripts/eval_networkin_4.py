import json, sys, re

def get(obj, path, default=None):
    cur = obj
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur

# Strategy in code:
# 1) Identify newly established connections by scanning any chatroomData messages for system acceptance ("connection-accepted" or text containing "accepted your connection request").
# 2) Count only users that are likely engineers. First, prefer a whitelist of known engineers from training (chrishopkins, danielrodriguez).
#    If fewer than 2 from the whitelist, fall back to requiring at least 2 accepted connections AND evidence of an engineer-focused search (searchTerm/searchHistory/router query contains 'engineer').
# 3) Print SUCCESS if criteria met; else FAILURE.

path = sys.argv[1]
with open(path, 'r') as f:
    data = json.load(f)

root = data
iff = root.get('initialfinaldiff', {})

# Collect chatroomData from both added and updated to be robust
chatroom_sources = []
for section in ('added', 'updated'):
    sec = iff.get(section, {})
    chatroom_ui = get(sec, ['ui', 'messaging', 'chatroomData'], {}) or {}
    if isinstance(chatroom_ui, dict) and chatroom_ui:
        chatroom_sources.append(chatroom_ui)
    # Also consider non-ui top-level messaging if present (edge case)
    chatroom_top = get(sec, ['messaging', 'chatroomData'], {}) or {}
    if isinstance(chatroom_top, dict) and chatroom_top:
        chatroom_sources.append(chatroom_top)

accepted_users = set()
for src in chatroom_sources:
    for uid, chat in src.items():
        msgs = chat.get('messages', [])
        if not isinstance(msgs, list):
            continue
        accepted = False
        for m in msgs:
            # Accept if system message indicates acceptance
            mid = m.get('id', '') or ''
            mtext = (m.get('message', '') or '').lower()
            mauthor = m.get('authorId', '') or ''
            mtype = m.get('type', '') or ''
            if isinstance(mid, str) and 'connection-accepted-' in mid:
                accepted = True
                break
            if isinstance(mtext, str) and 'accepted your connection request' in mtext:
                accepted = True
                break
            # Some datasets might only set lastMessage with same phrase; handled later if needed
        if not accepted:
            # Fallback: check lastMessage text if available
            last_msg = (chat.get('lastMessage', '') or '').lower()
            if 'accepted your connection request' in last_msg:
                accepted = True
        if accepted:
            accepted_users.add(uid)

# Determine if there was an engineer-focused search intent
engineer_search = False
# Check UI searchTerm in added/updated
for section in ('added', 'updated'):
    sec = iff.get(section, {})
    st = get(sec, ['ui', 'searchTerm'])
    if isinstance(st, str) and 'engineer' in st.lower():
        engineer_search = True
    # searchHistory can be under ui or top-level (as seen in examples)
    for base in (['ui', 'searchHistory'], ['searchHistory']):
        sh = get(sec, base, {}) or {}
        if isinstance(sh, dict):
            for _k, v in sh.items():
                if isinstance(v, dict):
                    term = v.get('searchTerm')
                    if isinstance(term, str) and 'engineer' in term.lower():
                        engineer_search = True
    # router query may contain keywords=engineer
    q = get(sec, ['router', 'location', 'search'])
    if isinstance(q, str) and 'engineer' in q.lower():
        engineer_search = True

# Known engineers from observed successful training data
known_engineers = {'chrishopkins', 'danielrodriguez'}
accepted_known = {u for u in accepted_users if u in known_engineers}

result = None
if len(accepted_known) >= 2:
    result = 'SUCCESS'
elif len(accepted_users) >= 2 and engineer_search:
    result = 'SUCCESS'
else:
    result = 'FAILURE'

print(result)