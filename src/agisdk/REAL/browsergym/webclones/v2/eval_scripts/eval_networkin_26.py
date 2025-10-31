import json, sys

def contains_software_engineer(text: str) -> bool:
    if not isinstance(text, str):
        return False
    s = text.lower()
    return ('software' in s) and ('engineer' in s)


def parse_keywords_from_query(query: str) -> str:
    # Extract value after 'keywords=' up to '&'; perform minimal decoding for + and %20
    if not isinstance(query, str):
        return ''
    if 'keywords=' not in query:
        return ''
    tail = query.split('keywords=', 1)[1]
    val = tail.split('&', 1)[0]
    # Minimal decoding
    val = val.replace('+', ' ').replace('%20', ' ')
    return val


def search_for_software_engineer(data) -> bool:
    found = False

    def recurse(obj):
        nonlocal found
        if found:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                # Check explicit searchTerm fields
                if k == 'searchTerm' and isinstance(v, str):
                    if contains_software_engineer(v):
                        found = True
                        return
                # Check router query strings containing keywords
                if k == 'search' and isinstance(v, str):
                    kw = parse_keywords_from_query(v)
                    if kw and contains_software_engineer(kw):
                        found = True
                        return
                # Recurse deeper
                recurse(v)
        elif isinstance(obj, list):
            for item in obj:
                if found:
                    return
                recurse(item)
        # Ignore other types

    # Focus on the diff content but allow scanning entire json for robustness
    recurse(data)
    return found


def message_indicates_reach_out(data) -> bool:
    # Check any message/lastMessage text for advice-seeking language and software context
    advice_terms = ['advice', 'tip', 'tips', 'guidance', 'mentor', 'mentorship', 'reach out', 'connect']

    def has_advice_and_software(text: str) -> bool:
        if not isinstance(text, str):
            return False
        t = text.lower()
        return ('software' in t) and any(term in t for term in advice_terms)

    def recurse(obj) -> bool:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ('message', 'lastMessage') and isinstance(v, str):
                    if has_advice_and_software(v):
                        return True
                if recurse(v):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if recurse(item):
                    return True
        return False

    return recurse(data)


def main():
    import sys
    if len(sys.argv) < 2:
        print('FAILURE')
        return
    path = sys.argv[1]
    try:
        with open(path, 'r') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    # Strategy: success if there is clear evidence of a search for "Software engineer" OR
    # if a message text indicates reaching out for advice in a software context.
    searched = search_for_software_engineer(data)
    reached_out = message_indicates_reach_out(data)

    if searched or reached_out:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()