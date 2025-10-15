import sys, json

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Determine if a job title corresponds to backend or full stack developer
def is_target_role(job_title):
    if not isinstance(job_title, str):
        return False
    s = job_title.strip().lower()
    # Normalize common variations
    return (
        'backend' in s or 'back-end' in s or
        'full-stack' in s or 'full stack' in s or 'fullstack' in s
    )

# Extract all contact entries from a contactList which might be dict or list
def iter_contacts(contact_list):
    if not contact_list:
        return
    if isinstance(contact_list, dict):
        # Keys may be string indices
        for v in contact_list.values():
            if isinstance(v, dict):
                yield v
    elif isinstance(contact_list, list):
        for v in contact_list:
            if isinstance(v, dict):
                yield v

# Extract all message texts authored by Client from a contact entry
def client_texts_from_contact(contact):
    texts = []
    # Check lastMessage if authored by Client
    last_author = contact.get('lastMessageAuthor')
    last_msg = contact.get('lastMessage')
    if isinstance(last_author, str) and last_author.strip().lower() == 'client' and isinstance(last_msg, str):
        texts.append(last_msg)

    # Check messages container which can be dict or list
    msgs = contact.get('messages')
    if isinstance(msgs, dict):
        for m in msgs.values():
            if isinstance(m, dict):
                author = m.get('author')
                msg = m.get('message')
                if isinstance(author, str) and author.strip().lower() == 'client' and isinstance(msg, str):
                    texts.append(msg)
    elif isinstance(msgs, list):
        for m in msgs:
            if isinstance(m, dict):
                author = m.get('author')
                msg = m.get('message')
                if isinstance(author, str) and author.strip().lower() == 'client' and isinstance(msg, str):
                    texts.append(msg)
    return texts

# Determine whether a given text constitutes an invite message per task
def is_invite_message(text):
    if not isinstance(text, str):
        return False
    t = text.strip().lower()
    # Must clearly reference building a fitness app
    if 'fitness app' not in t:
        return False
    # Must show intent to build
    if 'build' not in t and 'building' not in t:
        return False
    # Must be an invitation/question expressing interest
    invite_cues = ['interested', 'would you like', "would u like", 'want to', 'wanna']
    if not any(cue in t for cue in invite_cues):
        return False
    return True


def main():
    try:
        path = sys.argv[1]
    except Exception:
        print('FAILURE')
        return

    data = load_json(path)

    # Navigate to initialfinaldiff
    root = data.get('initialfinaldiff', data)

    found_success = False

    # Search both updated and added sections for messages.contactList
    for section_key in ['updated', 'added']:
        section = root.get(section_key, {}) if isinstance(root, dict) else {}
        messages = section.get('messages', {}) if isinstance(section, dict) else {}
        contact_list = messages.get('contactList') if isinstance(messages, dict) else None
        for contact in iter_contacts(contact_list):
            job_title = contact.get('job')
            if not is_target_role(job_title):
                continue
            texts = client_texts_from_contact(contact)
            for txt in texts:
                if is_invite_message(txt):
                    found_success = True
                    break
            if found_success:
                break
        if found_success:
            break

    print('SUCCESS' if found_success else 'FAILURE')

if __name__ == '__main__':
    main()
