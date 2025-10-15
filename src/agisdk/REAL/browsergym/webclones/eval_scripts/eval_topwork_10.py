import json, sys, re

def parse_number(val):
    # Robust numeric parsing for rates that may be int/float/str with symbols
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        s = val.strip().replace(',', '')
        # Remove common currency symbols
        s = s.replace('$', '')
        try:
            return float(s)
        except Exception:
            return None
    return None

# Strategy:
# - Load final_state_diff.json and inspect initialfinaldiff.added.jobs.jobs for job postings.
# - Declare SUCCESS if there exists at least one job with:
#   * title mentions "financial" and "analyst" (case-insensitive)
#   * hourlyRateFrom and hourlyRateTo are numbers within [45, 65] and from <= to
#   * status == "published"
# - Otherwise, FAILURE.

def find_jobs(data):
    jobs = []
    root = data.get('initialfinaldiff', {})
    # Primary source: added.jobs.jobs
    added_jobs_map = (
        root.get('added', {})
            .get('jobs', {})
            .get('jobs', {})
    )
    if isinstance(added_jobs_map, dict):
        jobs.extend(v for v in added_jobs_map.values() if isinstance(v, dict))
    # Fallback: if nothing there, try updated.jobs.jobs (unlikely but defensive)
    if not jobs:
        updated_jobs_map = (
            root.get('updated', {})
                .get('jobs', {})
                .get('jobs', {})
        )
        if isinstance(updated_jobs_map, dict):
            jobs.extend(v for v in updated_jobs_map.values() if isinstance(v, dict))
    return jobs


def title_matches_financial_analyst(title):
    if not isinstance(title, str):
        return False
    t = title.strip().lower()
    # Accept if phrase appears, or both tokens appear in any order
    if 'financial analyst' in t:
        return True
    return ('financial' in t and 'analyst' in t)


def job_matches(job):
    title = job.get('title')
    status = job.get('status')
    if not title_matches_financial_analyst(title):
        return False
    if status is not None and str(status).lower() != 'published':
        # If status exists and is not published, do not accept
        return False
    frm = parse_number(job.get('hourlyRateFrom'))
    to = parse_number(job.get('hourlyRateTo'))
    if frm is None or to is None:
        return False
    if frm > to:
        return False
    # Rates must be within 45 to 65 inclusive
    if not (45 <= frm <= 65 and 45 <= to <= 65):
        return False
    return True


def main():
    try:
        path = sys.argv[1]
    except IndexError:
        print('FAILURE')
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print('FAILURE')
        return

    jobs = find_jobs(data)
    success = any(job_matches(j) for j in jobs)
    print('SUCCESS' if success else 'FAILURE')

if __name__ == '__main__':
    main()