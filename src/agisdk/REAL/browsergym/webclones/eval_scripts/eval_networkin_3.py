import sys, json

def safe_get(d, *keys):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur

def main():
    if len(sys.argv) < 2:
        print("FAILURE")
        return
    path = sys.argv[1]
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    initialfinaldiff = data.get('initialfinaldiff')
    if not isinstance(initialfinaldiff, dict):
        print("FAILURE")
        return

    # We only consider items in the 'added' section to ensure they were created in this run
    added = initialfinaldiff.get('added')
    if not isinstance(added, dict):
        # No additions means no new connections made in this run
        print("FAILURE")
        return

    ui = added.get('ui', {}) if isinstance(added.get('ui', {}), dict) else {}
    messaging = ui.get('messaging', {}) if isinstance(ui.get('messaging', {}), dict) else {}
    chatrooms = messaging.get('chatroomData', {}) if isinstance(messaging.get('chatroomData', {}), dict) else {}

    connected_profiles = set()

    # Strategy 1: Detect acceptance messages in chat history indicating a successful new connection
    for key, room in chatrooms.items():
        if not isinstance(room, dict):
            continue
        profile_id = room.get('profileId') or room.get('id') or key
        msgs = room.get('messages', [])
        if not isinstance(msgs, list):
            msgs = []
        accepted_here = False
        for m in msgs:
            if not isinstance(m, dict):
                continue
            msg_text = str(m.get('message', '')).lower()
            msg_id = str(m.get('id', '')).lower()
            # Look for explicit acceptance signals
            if 'accepted your connection request' in msg_text or 'connection-accepted-' in msg_id:
                accepted_here = True
                break
        if accepted_here and profile_id:
            connected_profiles.add(str(profile_id))

    # Strategy 2: Use added connectionGrades with value '1st' as additional confirmation of a new first-degree connection
    profiles_section = ui.get('profiles', {}) if isinstance(ui.get('profiles', {}), dict) else {}
    connection_grades = profiles_section.get('connectionGrades', {}) if isinstance(profiles_section.get('connectionGrades', {}), dict) else {}
    for pid, grade in connection_grades.items():
        if isinstance(grade, str) and grade.strip().lower() == '1st':
            connected_profiles.add(str(pid))

    # Determine success: need at least 3 unique new connections in this run
    if len(connected_profiles) >= 3:
        print("SUCCESS")
    else:
        print("FAILURE")

if __name__ == '__main__':
    main()
