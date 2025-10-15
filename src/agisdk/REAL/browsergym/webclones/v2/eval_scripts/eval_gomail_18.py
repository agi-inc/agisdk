import sys, json

def strip_html(text: str) -> str:
    # Remove HTML tags without using regex; drop characters between < and >
    if text is None:
        return ''
    s = []
    in_tag = False
    for ch in text:
        if ch == '<':
            in_tag = True
            continue
        if ch == '>':
            in_tag = False
            continue
        if not in_tag:
            s.append(ch)
    out = ''.join(s)
    # Replace common HTML entities and trim
    out = out.replace('&nbsp;', ' ')
    return out.strip()

def is_non_empty_content(html: str) -> bool:
    stripped = strip_html(html)
    # Also consider if content is just whitespace/newlines after stripping
    return len(stripped.strip()) > 0

def main():
    # Strategy: Find emails added in this run that are sent to exactly and only charles.davis@example.com
    # Count qualifying emails with non-empty content; success iff exactly one such email exists.
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    diffs = data.get('differences') or {}
    emails = diffs.get('emails') or {}
    added = emails.get('added') or []
    if not isinstance(added, list):
        added = []

    target = 'charles.davis@example.com'
    qualifying = 0

    for em in added:
        if not isinstance(em, dict):
            continue
        # Must be a sent email (avoid drafts)
        if not em.get('sent', False):
            continue
        # Extract and normalize recipients
        to_list = em.get('to') or []
        if not isinstance(to_list, list):
            continue
        norm_to = []
        for addr in to_list:
            if isinstance(addr, str):
                norm_to.append(addr.strip().lower())
        # Must be exactly one recipient and it must be the target
        if len(norm_to) != 1 or norm_to[0] != target:
            continue
        # Content must be non-empty (after stripping HTML)
        content = em.get('content')
        if not isinstance(content, str):
            content = '' if content is None else str(content)
        if not is_non_empty_content(content):
            continue
        qualifying += 1

    if qualifying == 1:
        print('SUCCESS')
    else:
        print('FAILURE')

if __name__ == '__main__':
    main()
