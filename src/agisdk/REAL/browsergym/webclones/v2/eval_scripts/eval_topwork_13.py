import json, sys

def to_lower_str(x):
    if isinstance(x, str):
        return x.strip().lower()
    return None

def to_int_safe(x):
    try:
        # handle strings like '20', numbers, etc.
        if isinstance(x, bool):
            return None
        if isinstance(x, (int, float)):
            return int(x)
        if isinstance(x, str):
            x = x.strip()
            # allow numeric strings only
            if x.replace('.', '', 1).isdigit():
                return int(float(x))
        return None
    except Exception:
        return None

# Verification script
# Strategy:
# - Identify newly added jobs in initialfinaldiff.added.jobs.jobs
# - Find a job with title containing 'Data Annotator' and description mentioning 'Verita AI'
# - Validate key fields: hourlyRateFrom=20, hourlyRateTo=25, estimateSize=small, estimateTime=1 to 3 months,
#   estimateLevelExperience=entry, estimateHireOpportunity=no, and status=published
# - Print SUCCESS if any job matches; otherwise, FAILURE

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

    initialfinaldiff = data.get('initialfinaldiff', {}) or {}
    added = initialfinaldiff.get('added', {}) or {}
    jobs_root = added.get('jobs', {}) or {}
    jobs_dict = jobs_root.get('jobs', {}) or {}

    # Collect job entries from the added jobs
    job_entries = []
    if isinstance(jobs_dict, dict):
        for v in jobs_dict.values():
            if isinstance(v, dict):
                job_entries.append(v)

    success = False
    for job in job_entries:
        title = to_lower_str(job.get('title'))
        desc = to_lower_str(job.get('description'))
        if not title or not desc:
            continue
        if 'data annotator' not in title:
            continue
        if 'verita ai' not in desc:
            continue

        hr_from = to_int_safe(job.get('hourlyRateFrom'))
        hr_to = to_int_safe(job.get('hourlyRateTo'))
        size = to_lower_str(job.get('estimateSize'))
        timeframe = to_lower_str(job.get('estimateTime'))
        level = to_lower_str(job.get('estimateLevelExperience'))
        hire = to_lower_str(job.get('estimateHireOpportunity'))
        status = to_lower_str(job.get('status'))

        if hr_from != 20 or hr_to != 25:
            continue
        if size != 'small':
            continue
        if timeframe != '1 to 3 months':
            continue
        if level != 'entry':
            continue
        if hire != 'no':
            continue
        if status != 'published':
            continue

        # All checks passed
        success = True
        break

    print("SUCCESS" if success else "FAILURE")

if __name__ == '__main__':
    main()
