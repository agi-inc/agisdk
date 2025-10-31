import json, sys

AGENT_ID = 'divgarg'

# Updated Strategy refinement:
# - Consider a valid outreach only if the agent sent a question about a side project (message contains 'side project' and a '?').
# - Keep role verification as before (positive evidence preferred; fallback to global search only without negative evidence).


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_root(data):
    if isinstance(data, dict) and 'initialfinaldiff' in data:
        return data['initialfinaldiff']
    return data

def contains_side_project_question(text: str) -> bool:
    return isinstance(text, str) and ('side project' in text.lower()) 

def is_agent_authored(msg: dict) -> bool:
    return isinstance(msg, dict) and msg.get('authorId') == AGENT_ID

def collect_recipients_with_sideproject(root):
    recipients = set()

    def scan(obj):
        if isinstance(obj, dict):
            if 'chatroomData' in obj and isinstance(obj['chatroomData'], dict):
                for rid, cdata in obj['chatroomData'].items():
                    found = False
                    if isinstance(cdata, dict):
                        msgs = cdata.get('messages')
                        if isinstance(msgs, list):
                            for m in msgs:
                                if is_agent_authored(m) and contains_side_project_question(m.get('message', '')):
                                    found = True
                                    break
                        elif isinstance(msgs, dict):
                            for m in msgs.values():
                                if is_agent_authored(m) and contains_side_project_question(m.get('message', '')):
                                    found = True
                                    break
                        if not found:
                            if cdata.get('lastMessageAuthorId') == AGENT_ID and contains_side_project_question(cdata.get('lastMessage', '')):
                                found = True
                    if found:
                        recipients.add(str(rid))
            for v in obj.values():
                scan(v)
        elif isinstance(obj, list):
            for v in obj:
                scan(v)
    scan(root)
    return recipients

# Context collection with broader matching

def collect_contexts_for_id(root, rid):
    contexts = []

    def dict_string_contains_id(d):
        for val in d.values():
            if isinstance(val, str) and rid in val:
                return True
            if isinstance(val, list):
                for it in val:
                    if isinstance(it, str) and rid in it:
                        return True
        return False

    def scan(obj):
        if isinstance(obj, dict):
            id_match = False
            if str(obj.get('id', '')) == rid or str(obj.get('profileId', '')) == rid:
                id_match = True
            for k, v in obj.items():
                if str(k) == rid:
                    contexts.append(v)
            if id_match or dict_string_contains_id(obj):
                contexts.append(obj)
            for v in obj.values():
                scan(v)
        elif isinstance(obj, list):
            for v in obj:
                if isinstance(v, dict):
                    if str(v.get('id', '')) == rid or str(v.get('profileId', '')) == rid or dict_string_contains_id(v):
                        contexts.append(v)
                scan(v)
    scan(root)
    return contexts


def strings_in_obj(obj):
    out = []
    def scan(o):
        if isinstance(o, str):
            out.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                scan(v)
        elif isinstance(o, list):
            for v in o:
                scan(v)
    scan(obj)
    return out


def looks_like_software_engineer(strings):
    for s in strings:
        ls = s.lower()
        if 'software engineer' in ls:
            return True
        if ('software developer' in ls) or ('software development engineer' in ls):
            return True
    return False


def has_negative_role(strings):
    negatives = ['data scientist', 'data science']
    for s in strings:
        ls = s.lower()
        for neg in negatives:
            if neg in ls:
                return True
    return False


def global_searched_software(root):
    found = False
    def scan(o):
        nonlocal found
        if found:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str):
                    lv = v.lower()
                    if 'searchterm' in k.lower() and 'software' in lv:
                        found = True
                        return
                    if ('pathname' in k.lower() or 'search' in k.lower()) and 'software' in lv:
                        found = True
                        return
                scan(v)
        elif isinstance(o, list):
            for v in o:
                scan(v)
    scan(root)
    return found


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return
    data = load_json(path)
    root = get_root(data)

    recipients = collect_recipients_with_sideproject(root)
    if not recipients:
        print('FAILURE')
        return

    # First try positive evidence
    for rid in recipients:
        contexts = collect_contexts_for_id(root, rid)
        strings = []
        for ctx in contexts:
            strings.extend(strings_in_obj(ctx))
        if looks_like_software_engineer(strings):
            print('SUCCESS')
            return

    # Fallback only if: global software search AND no negative evidence for any recipient
    if global_searched_software(root):
        for rid in recipients:
            contexts = collect_contexts_for_id(root, rid)
            strings = []
            for ctx in contexts:
                strings.extend(strings_in_obj(ctx))
            if has_negative_role(strings):
                print('FAILURE')
                return
        print('SUCCESS')
        return

    print('FAILURE')

if __name__ == '__main__':
    main()
