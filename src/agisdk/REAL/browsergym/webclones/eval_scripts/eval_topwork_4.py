import sys, json

def get(d, path, default=None):
    cur = d
    for k in path:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def is_number(x):
    try:
        float(x)
        return True
    except Exception:
        return False


def check_job(job):
    # Core verification logic based on task: ensure a Data Annotator job for Verita AI with correct pay and key fields
    if not isinstance(job, dict):
        return False

    title = str(job.get('title', '')).strip().lower()
    if 'data annotator' not in title:
        return False

    desc = str(job.get('description', '')).lower()
    if 'verita ai' not in desc:
        return False

    # Validate hourly pay is exactly 20-25 per hour
    hr_from = job.get('hourlyRateFrom')
    hr_to = job.get('hourlyRateTo')
    if not (is_number(hr_from) and is_number(hr_to)):
        return False
    hr_from = float(hr_from)
    hr_to = float(hr_to)
    # Require exact match 20 to 25 to avoid wrong pay (e.g., 200-250 in failed example)
    if not (abs(hr_from - 20) < 1e-9 and abs(hr_to - 25) < 1e-9):
        return False

    # Validate key fields reflecting a small, entry-level, non-permanent job
    size = str(job.get('estimateSize', '')).lower()
    if size != 'small':
        return False

    level = str(job.get('estimateLevelExperience', '')).lower()
    if level != 'entry':
        return False

    hire_opp = str(job.get('estimateHireOpportunity', '')).lower()
    if hire_opp != 'no':
        return False

    # Duration should be short-term; allow common valid value(s)
    time_str = str(job.get('estimateTime', ''))
    allowed_times = {"1 to 3 months", "Less than 1 month"}
    if time_str not in allowed_times:
        return False

    # If all checks pass, consider this a valid posting
    return True


def main():
    try:
        path = sys.argv[1]
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        print("FAILURE")
        return

    # Extract added jobs; be defensive about structure
    jobs_container = get(data, ["initialfinaldiff", "added", "jobs", "jobs"], default={})
    valid_found = False

    if isinstance(jobs_container, dict):
        for _, job in jobs_container.items():
            if check_job(job):
                valid_found = True
                break

    print("SUCCESS" if valid_found else "FAILURE")

if __name__ == '__main__':
    main()
