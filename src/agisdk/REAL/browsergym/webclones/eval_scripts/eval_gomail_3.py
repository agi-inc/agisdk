import json, sys, re

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Simple HTML tag stripper to detect non-empty content
TAG_RE = re.compile(r'<[^>]+>')

def strip_html(text):
    if not isinstance(text, str):
        return ''
    return TAG_RE.sub('', text or '').strip()

# Collect added emails from both structures
def get_added_emails(data):
    added = []
    # differences.emails.added (list of email dicts)
    diffs = data.get('differences') if isinstance(data.get('differences'), dict) else {}
    emails_block = diffs.get('emails') if isinstance(diffs.get('emails'), dict) else {}
    for item in emails_block.get('added', []) or []:
        if isinstance(item, dict):
            added.append(item)
    # initialfinaldiff.added.email.emails (mapping id -> email dict)
    i_fd = data.get('initialfinaldiff')
    if isinstance(i_fd, dict):
        added_block = i_fd.get('added') if isinstance(i_fd.get('added'), dict) else {}
        email_block = added_block.get('email') if isinstance(added_block.get('email'), dict) else {}
        emails_map = email_block.get('emails') if isinstance(email_block.get('emails'), dict) else {}
        for _id, item in emails_map.items():
            if isinstance(item, dict):
                added.append(item)
    return added

# Collect updates per id, aggregating flags like starred=false and trash=true
def get_updates_agg(data):
    agg = {}
    def ensure(id_):
        if id_ not in agg:
            agg[id_] = {'starred_set_false': False, 'trash_true': False, 'other_changes': set()}
        return agg[id_]

    diffs = data.get('differences') if isinstance(data.get('differences'), dict) else {}
    emails_block = diffs.get('emails') if isinstance(diffs.get('emails'), dict) else {}
    # differences.emails.updated: list of partial updates
    for upd in (emails_block.get('updated', []) or []):
        if not isinstance(upd, dict):
            continue
        id_ = str(upd.get('id')) if 'id' in upd else None
        if not id_:
            continue
        rec = ensure(id_)
        if 'starred' in upd and upd.get('starred') is False:
            rec['starred_set_false'] = True
        if upd.get('trash') is True:
            rec['trash_true'] = True
        for k, v in upd.items():
            if k not in ('id', 'starred', 'trash'):
                rec['other_changes'].add(k)

    # initialfinaldiff.updated.email.emails: mapping id -> partial updates
    i_fd = data.get('initialfinaldiff')
    if isinstance(i_fd, dict):
        upd_block = i_fd.get('updated') if isinstance(i_fd.get('updated'), dict) else {}
        email_block = upd_block.get('email') if isinstance(upd_block.get('email'), dict) else {}
        emails_updates = email_block.get('emails') if isinstance(email_block.get('emails'), dict) else {}
        for id_, upd in emails_updates.items():
            if not isinstance(upd, dict):
                continue
            id_s = str(id_)
            rec = ensure(id_s)
            if 'starred' in upd and upd.get('starred') is False:
                rec['starred_set_false'] = True
            if upd.get('trash') is True:
                rec['trash_true'] = True
            for k, v in upd.items():
                if k not in ('starred', 'trash'):
                    rec['other_changes'].add(k)

    return agg


def email_to_alexa_about_work_permit(added_emails):
    target = 'alexa.richardson@example.com'
    for em in added_emails:
        try:
            to_list = [str(t).lower() for t in (em.get('to') or [])]
            sent = bool(em.get('sent'))
            subject = (em.get('subject') or '')
            content = em.get('content') or ''
            content_text = strip_html(content)
            subj_l = subject.lower()
            cont_l = content_text.lower()
            mentions_work_permit = ('work permit' in subj_l) or ('work permit' in cont_l)
            non_empty_body = len(content_text.strip()) > 0
            if sent and any(t == target for t in to_list) and mentions_work_permit and non_empty_body:
                return True
        except Exception:
            continue
    return False


def cleared_all_starred(agg):
    # Conditions:
    # 1) Every trashed email must be one whose star was removed in this run (detect via starred=false update)
    # 2) A sufficient number of starred emails were cleared (dataset indicates many starred; set threshold conservatively to 10)
    starred_cleared_ids = [i for i, r in agg.items() if r['trash_true'] and r['starred_set_false']]
    non_starred_trashed_ids = [i for i, r in agg.items() if r['trash_true'] and not r['starred_set_false']]
    threshold = 10
    return len(non_starred_trashed_ids) == 0 and len(starred_cleared_ids) >= threshold


def main():
    path = sys.argv[1]
    data = load_json(path)

    added_emails = get_added_emails(data)
    agg_updates = get_updates_agg(data)

    cond_email = email_to_alexa_about_work_permit(added_emails)
    cond_starred = cleared_all_starred(agg_updates)

    if cond_email and cond_starred:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()